"""Validation and evidence-scoring seam for observability closure campaigns."""

# ruff: noqa: F403, F405

from __future__ import annotations

from scripts.engineering.qa.run_observability_closure_campaign import *
from scripts.engineering.qa.run_observability_closure_campaign import _sha256_file


def _parse_generated_at(value: object) -> bool:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _validate_summary(key: str, summary: object) -> list[str]:
    if not isinstance(summary, dict):
        return ["summary must be an object"]
    errors: list[str] = []
    for field_name, expected in EVIDENCE_SUMMARY_REQUIREMENTS[key].items():
        value = summary.get(field_name)
        if type(value) is not int:
            errors.append(f"summary.{field_name} must be an integer")
        elif (
            field_name.endswith(
                (
                    "count",
                    "mismatch_count",
                    "failure_count",
                    "unstable_count",
                    "drift_count",
                    "missing_count",
                )
            )
            and expected == 0
        ):
            if value != 0:
                errors.append(f"summary.{field_name} must equal 0")
        elif value < expected:
            errors.append(f"summary.{field_name} must be >= {expected}")
    return errors


def _validate_evidence_producer(key: str, producer: object) -> list[str]:
    if not isinstance(producer, dict):
        return ["producer must be an object"]
    errors: list[str] = []
    command = producer.get("command")
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(item, str) and item.strip() for item in command)
    ):
        errors.append("producer.command must be a non-empty string array")
    if producer.get("exit_code") != 0:
        errors.append("producer.exit_code must equal 0")
    if isinstance(command, list) and (
        len(command) < 6
        or command[1:3] != ["-m", CANONICAL_EVIDENCE_ASSEMBLER]
        or "--category" not in command
        or key not in command
    ):
        errors.append(
            "producer.command must use the canonical typed evidence assembler"
        )
    if key == "promtool" and producer.get("tool_version") != "3.13.1":
        errors.append("producer.tool_version must equal pinned 3.13.1")
    return errors


def _validate_evidence_assertions(assertions: object) -> list[str]:
    if not isinstance(assertions, list) or not assertions:
        return ["assertions must be a non-empty array"]
    errors: list[str] = []
    for index, assertion in enumerate(assertions):
        if not isinstance(assertion, dict):
            errors.append(f"assertions[{index}] must be an object")
            continue
        if not str(assertion.get("name") or "").strip():
            errors.append(f"assertions[{index}].name must be non-empty")
        if assertion.get("status") != "pass":
            errors.append(f"assertions[{index}].status must equal pass")
        if assertion.get("actual") != assertion.get("expected"):
            errors.append(f"assertions[{index}] actual must equal expected")
    return errors


def _validate_one_raw_artifact(
    index: int,
    artifact: object,
    *,
    raw_root: Path,
    seen_paths: set[Path],
) -> tuple[list[str], dict[str, str] | None, str]:
    """Validate one raw evidence artifact entry; returns errors, retained row, kind."""
    if not isinstance(artifact, dict):
        return [f"raw_artifacts[{index}] must be an object"], None, ""
    path = Path(str(artifact.get("path") or "")).expanduser().resolve()
    kind = str(artifact.get("kind") or "").strip()
    expected_sha256 = str(artifact.get("sha256") or "").strip()
    errors: list[str] = []
    if raw_root not in path.parents:
        errors.append(f"raw_artifacts[{index}] must be inside AUDIT_ROOT/evidence/raw")
    if path in seen_paths:
        errors.append(f"raw_artifacts[{index}] duplicates another raw artifact")
    seen_paths.add(path)
    if not path.is_file():
        errors.append(f"raw_artifacts[{index}] is not a file")
        return errors, None, kind
    actual_sha256 = _sha256_file(path)
    if expected_sha256 != actual_sha256:
        errors.append(f"raw_artifacts[{index}].sha256 does not match content")
    if not kind:
        errors.append(f"raw_artifacts[{index}].kind must be non-empty")
    retained = {"path": str(path), "sha256": actual_sha256, "kind": kind}
    return errors, retained, kind


def _validate_prometheus_reconciliation_rows(
    prometheus: list[dict[str, object]],
) -> tuple[list[str], dict[tuple[str, str], dict[str, object]]]:
    errors: list[str] = []
    prom_by_key: dict[tuple[str, str], dict[str, object]] = {}
    for payload in prometheus:
        key = (str(payload.get("pipeline") or ""), str(payload.get("run_id") or ""))
        if not all(key) or key in prom_by_key:
            errors.append("Prometheus rows require unique pipeline/run_id anchors")
        prom_by_key[key] = payload
        if payload.get("status") != "success":
            errors.append(
                "Prometheus reconciliation responses must report status=success"
            )
        if payload.get("pipeline_runs_total_delta") != 1:
            errors.append(
                "each terminal run must increment pipeline_runs_total exactly once"
            )
        if payload.get("health_probe_counter_delta") != 0:
            errors.append("pipeline completion must not change health-probe counters")
    return errors, prom_by_key


def _validate_ledger_reconciliation_rows(
    ledgers: list[dict[str, object]],
) -> tuple[list[str], dict[tuple[str, str], dict[str, object]]]:
    errors: list[str] = []
    ledger_by_key: dict[tuple[str, str], dict[str, object]] = {}
    for payload in ledgers:
        key = (str(payload.get("pipeline") or ""), str(payload.get("run_id") or ""))
        if not all(key) or key in ledger_by_key:
            errors.append("ledger rows require unique pipeline/run_id anchors")
        ledger_by_key[key] = payload
        events = payload.get("events")
        terminal = (
            [
                event
                for event in events
                if isinstance(event, dict)
                and event.get("event_type") in TERMINAL_EVENTS
            ]
            if isinstance(events, list)
            else []
        )
        if len(terminal) != 1:
            errors.append(
                "each ledger snapshot must contain exactly one terminal event"
            )
        if payload.get("terminal_run_result_count") != 1:
            errors.append("each ledger snapshot must reconcile one terminal RunResult")
    return errors, ledger_by_key


def _validate_dq_reconciliation_row(dq_rows: list[dict[str, object]]) -> list[str]:
    if len(dq_rows) != 1:
        return ["metric reconciliation requires one focused DQ anomaly row"]
    dq_row = dq_rows[0]
    if (
        dq_row.get("source_present") is not True
        or dq_row.get("metric") != "bioetl_dq_anomaly_detected"
        or dq_row.get("delta") != 1
        or not str(dq_row.get("test_node_id") or "").strip()
    ):
        return ["focused DQ failure must increment one present anomaly metric"]
    return []


def _require_nonempty_fields(
    row: dict[str, object],
    field_names: tuple[str, ...],
    *,
    prefix: str,
) -> list[str]:
    """Return errors for blank required string fields on one row."""
    errors: list[str] = []
    for field_name in field_names:
        if not str(row.get(field_name) or "").strip():
            errors.append(f"{prefix} {field_name} must be non-empty")
    return errors


def _validate_one_workflow_child(
    child: dict[str, object],
    child_by_anchor: dict[tuple[str, str], dict[str, object]],
) -> list[str]:
    """Validate one workflow child row and register its anchor."""
    errors = _require_nonempty_fields(
        child,
        (
            "workflow_run_id",
            "run_id",
            "manifest_id",
            "workflow_name",
            "workflow_step_id",
        ),
        prefix="child",
    )
    if child.get("terminal_event") not in TERMINAL_EVENTS:
        errors.append("child terminal_event must be run_finished or run_failed")
    anchor = (
        str(child.get("run_id") or ""),
        str(child.get("manifest_id") or ""),
    )
    if all(anchor):
        if anchor in child_by_anchor:
            errors.append("child run/manifest anchors must be unique")
        child_by_anchor[anchor] = child
    return errors


def _validate_workflow_child_rows(
    children: list[dict[str, object]],
) -> tuple[list[str], dict[tuple[str, str], dict[str, object]]]:
    errors: list[str] = []
    child_by_anchor: dict[tuple[str, str], dict[str, object]] = {}
    for child in children:
        errors.extend(_validate_one_workflow_child(child, child_by_anchor))
    return errors, child_by_anchor


def _parent_child_field_mismatches(
    parent: dict[str, object],
    child: dict[str, object],
) -> list[str]:
    """Return reciprocal-field mismatches between parent and child rows."""
    errors: list[str] = []
    for field_name in ("workflow_run_id", "workflow_name", "workflow_step_id"):
        if str(child.get(field_name) or "") != str(parent.get(field_name) or ""):
            errors.append(
                f"parent/child {field_name} must match for reciprocal anchors"
            )
    return errors


def _validate_one_workflow_parent(
    parent: dict[str, object],
    *,
    child_by_anchor: dict[tuple[str, str], dict[str, object]],
    parent_ids: set[str],
    repeated_steps: dict[tuple[str, str], list[dict[str, object]]],
) -> list[str]:
    """Validate one workflow parent row and update aggregate indexes."""
    errors = _require_nonempty_fields(
        parent,
        (
            "workflow_run_id",
            "workflow_name",
            "workflow_step_id",
            "child_run_id",
            "child_manifest_id",
        ),
        prefix="parent",
    )
    workflow_run_id = str(parent.get("workflow_run_id") or "")
    if workflow_run_id:
        parent_ids.add(workflow_run_id)
    repeated_steps.setdefault(
        (
            str(parent.get("workflow_name") or ""),
            str(parent.get("workflow_step_id") or ""),
        ),
        [],
    ).append(parent)
    anchor = (
        str(parent.get("child_run_id") or ""),
        str(parent.get("child_manifest_id") or ""),
    )
    child = child_by_anchor.get(anchor)
    if child is None:
        errors.append("parent child run/manifest anchors must resolve to a child")
        return errors
    errors.extend(_parent_child_field_mismatches(parent, child))
    return errors


def _validate_workflow_parent_rows(
    parents: list[dict[str, object]],
    child_by_anchor: dict[tuple[str, str], dict[str, object]],
) -> tuple[list[str], set[str], dict[tuple[str, str], list[dict[str, object]]]]:
    errors: list[str] = []
    parent_ids: set[str] = set()
    repeated_steps: dict[tuple[str, str], list[dict[str, object]]] = {}
    for parent in parents:
        errors.extend(
            _validate_one_workflow_parent(
                parent,
                child_by_anchor=child_by_anchor,
                parent_ids=parent_ids,
                repeated_steps=repeated_steps,
            )
        )
    return errors, parent_ids, repeated_steps


def _has_repeated_success_and_failure(
    repeated_steps: dict[tuple[str, str], list[dict[str, object]]],
) -> bool:
    for (workflow_name, workflow_step_id), occurrences in repeated_steps.items():
        if not workflow_name or not workflow_step_id:
            continue
        distinct_runs = {
            str(parent.get("workflow_run_id") or "")
            for parent in occurrences
            if str(parent.get("workflow_run_id") or "")
        }
        statuses = {parent.get("status") for parent in occurrences}
        if len(distinct_runs) >= 2 and {"success", "failed"}.issubset(statuses):
            return True
    return False


def _validate_evidence_object_fields(
    key: str,
    payload: dict[str, object],
    *,
    source_revision: str,
    expected_binding: dict[str, object] | None,
    raw_root: Path,
) -> tuple[list[str], dict[str, int], list[dict[str, str]]]:
    """Field-level checks for one external evidence payload."""
    key_errors: list[str] = []
    summaries: dict[str, int] = {}
    if payload.get("schema_version") != 1:
        key_errors.append("schema_version must equal 1")
    if payload.get("evidence_type") != key:
        key_errors.append(f"evidence_type must equal {key}")
    if payload.get("status") != "pass":
        key_errors.append("status must equal pass")
    if payload.get("source_revision") != source_revision:
        key_errors.append("source_revision does not match campaign revision")
    if (
        expected_binding is not None
        and payload.get("campaign_binding") != expected_binding
    ):
        key_errors.append("campaign_binding does not match the executed campaign")
    if not _parse_generated_at(payload.get("generated_at")):
        key_errors.append("generated_at must be timezone-aware ISO-8601")
    key_errors.extend(_validate_summary(key, payload.get("summary")))
    summary_raw = payload.get("summary")
    if isinstance(summary_raw, dict):
        summaries = {
            str(field): value
            for field, value in summary_raw.items()
            if isinstance(field, str) and type(value) is int
        }
    key_errors.extend(_validate_evidence_producer(key, payload.get("producer")))
    key_errors.extend(_validate_evidence_assertions(payload.get("assertions")))
    raw_errors, retained = _validate_raw_artifacts(
        key,
        payload.get("raw_artifacts"),
        raw_root=raw_root,
    )
    key_errors.extend(raw_errors)
    if not raw_errors:
        key_errors.extend(_validate_raw_content(key, retained, expected_binding))
    return key_errors, summaries, retained


def _validate_sha256_artifact(label: str, artifact: object) -> list[str]:
    """Validate one path/sha256 artifact descriptor."""
    if not isinstance(artifact, dict):
        return [f"{label} must be an object"]
    path = Path(str(artifact.get("path") or ""))
    expected = str(artifact.get("sha256") or "")
    if not path.is_file():
        return [f"{label} is missing"]
    if _sha256_file(path) != expected:
        return [f"{label} hash changed after execution"]
    return []


def _validate_attempt_artifact_field(
    attempt: dict[str, object],
    *,
    attempt_index: int,
    field_name: str,
) -> list[str]:
    """Validate one artifact array field on a campaign attempt."""
    artifacts = attempt.get(field_name)
    if not isinstance(artifacts, list):
        return [f"attempts[{attempt_index}].{field_name} must be an array"]
    errors: list[str] = []
    for artifact_index, artifact in enumerate(artifacts):
        label = f"attempts[{attempt_index}].{field_name}[{artifact_index}]"
        errors.extend(_validate_sha256_artifact(label, artifact))
    return errors


def _validate_attempt_artifacts(attempts: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(attempts, list) or not attempts:
        return ["attempts must be a non-empty array"]
    for attempt_index, attempt in enumerate(attempts):
        if not isinstance(attempt, dict):
            errors.append(f"attempts[{attempt_index}] must be an object")
            continue
        for field_name in (
            "manifest_artifacts",
            "ledger_artifacts",
            "checkpoint_artifacts",
            "output_artifacts",
        ):
            errors.extend(
                _validate_attempt_artifact_field(
                    attempt,
                    attempt_index=attempt_index,
                    field_name=field_name,
                )
            )
    return errors


def _validate_workflow_phase_stream_artifacts(phases: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(phases, list) or not phases:
        return ["workflow phase evidence is missing"]
    for phase_index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            errors.append(f"workflow phase {phase_index} must be an object")
            continue
        for stream_name in ("stdout", "stderr"):
            label = f"workflow phase {phase_index} {stream_name}"
            path = Path(str(phase.get(f"{stream_name}_path") or ""))
            expected = str(phase.get(f"{stream_name}_sha256") or "")
            if not path.is_file():
                errors.append(f"{label} is missing")
            elif _sha256_file(path) != expected:
                errors.append(f"{label} hash changed after execution")
    return errors


def _validate_raw_artifacts(
    key: str,
    raw_artifacts: object,
    *,
    raw_root: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        return ["raw_artifacts must be a non-empty array"], []
    errors: list[str] = []
    retained: list[dict[str, str]] = []
    kind_counts: dict[str, int] = {}
    seen_paths: set[Path] = set()
    for index, artifact in enumerate(raw_artifacts):
        item_errors, row, kind = _validate_one_raw_artifact(
            index, artifact, raw_root=raw_root, seen_paths=seen_paths
        )
        errors.extend(item_errors)
        if row is None:
            continue
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        retained.append(row)
    for kind, minimum in EVIDENCE_RAW_KIND_REQUIREMENTS[key].items():
        if kind_counts.get(kind, 0) < minimum:
            errors.append(f"raw artifact kind {kind!r} requires at least {minimum}")
    return errors, retained


def _json_payloads_by_kind(
    retained: list[dict[str, str]], kind: str
) -> tuple[list[dict[str, object]], list[str]]:
    payloads: list[dict[str, object]] = []
    errors: list[str] = []
    for artifact in retained:
        if artifact["kind"] != kind:
            continue
        path = Path(artifact["path"])
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"{kind} artifact must be valid JSON: {exc}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"{kind} artifact payload must be an object")
            continue
        payloads.append(payload)
    return payloads, errors


def _tracing_pair_errors(
    payloads: list[dict[str, object]],
) -> list[str]:
    """Per-pipeline OFF/ON pair and signature parity errors."""
    errors: list[str] = []
    for pipeline in CHEMBL_PIPELINES:
        pair = [payload for payload in payloads if payload.get("pipeline") == pipeline]
        modes = {payload.get("tracing") for payload in pair}
        signatures = {str(payload.get("data_signature") or "") for payload in pair}
        if len(pair) != 2 or modes != {False, True}:
            errors.append(f"{pipeline} requires explicit OFF and ON results")
        if len(signatures) != 1 or "" in signatures:
            errors.append(
                f"{pipeline} tracing data signatures must be identical and non-empty"
            )
    return errors


def _expected_tracing_occurrences(
    expected_binding: dict[str, object],
) -> set[tuple[str, object, str, str]]:
    """Occurrence keys from executed standalone attempt binding."""
    expected_attempts = expected_binding.get("standalone_attempts")
    if not isinstance(expected_attempts, list):
        return set()
    return {
        (
            str(item.get("pipeline") or ""),
            item.get("tracing"),
            str((item.get("run_ids") or [""])[0]),
            str(item.get("result_signature") or ""),
        )
        for item in expected_attempts
        if isinstance(item, dict)
        and isinstance(item.get("run_ids"), list)
        and len(item["run_ids"]) == 1
    }


def _actual_tracing_occurrences(
    payloads: list[dict[str, object]],
) -> set[tuple[str, object, str, str]]:
    """Occurrence keys from retained attempt-result payloads."""
    return {
        (
            str(payload.get("pipeline") or ""),
            payload.get("tracing"),
            str(payload.get("run_id") or ""),
            str(payload.get("data_signature") or ""),
        )
        for payload in payloads
    }


def _tracing_coverage_errors(payloads: list[dict[str, object]]) -> list[str]:
    errors: list[str] = []
    pipelines = {str(payload.get("pipeline") or "") for payload in payloads}
    statuses = {payload.get("status") for payload in payloads}
    if pipelines != set(CHEMBL_PIPELINES):
        errors.append("tracing attempts must cover all 15 canonical pipelines")
    if statuses != {"success"}:
        errors.append("tracing attempt statuses must all equal success")
    return errors


def _validate_tracing_raw(
    retained: list[dict[str, str]],
    expected_binding: dict[str, object] | None = None,
) -> list[str]:
    payloads, errors = _json_payloads_by_kind(retained, "attempt-result")
    if len(payloads) != 30:
        return [*errors, "tracing parity requires exactly 30 attempt results"]
    errors.extend(_tracing_coverage_errors(payloads))
    errors.extend(_tracing_pair_errors(payloads))
    if expected_binding is not None and (
        _actual_tracing_occurrences(payloads)
        != _expected_tracing_occurrences(expected_binding)
    ):
        errors.append("tracing raw results do not match executed run occurrences")
    decision_traces = [payload.get("decision_trace") for payload in payloads]
    if not any(isinstance(trace, list) and trace for trace in decision_traces):
        errors.append(
            "at least one tracing attempt requires a non-empty decision trace"
        )
    return errors


def _validate_metric_reconciliation_raw(
    retained: list[dict[str, str]],
) -> list[str]:
    prometheus, errors = _json_payloads_by_kind(retained, "prometheus-response")
    ledgers, ledger_errors = _json_payloads_by_kind(retained, "ledger-snapshot")
    dq_rows, dq_errors = _json_payloads_by_kind(retained, "dq-anomaly-response")
    errors.extend(ledger_errors)
    errors.extend(dq_errors)
    if len(prometheus) != 15 or len(ledgers) != 15:
        errors.append("metric reconciliation requires 15 Prometheus and 15 ledger rows")
    prom_errors, prom_by_key = _validate_prometheus_reconciliation_rows(prometheus)
    ledger_errors2, ledger_by_key = _validate_ledger_reconciliation_rows(ledgers)
    errors.extend(prom_errors)
    errors.extend(ledger_errors2)
    if set(prom_by_key) != set(ledger_by_key):
        errors.append("Prometheus and ledger pipeline/run anchors must match exactly")
    if {pipeline for pipeline, _run_id in prom_by_key} != set(CHEMBL_PIPELINES):
        errors.append("metric reconciliation must cover all 15 canonical pipelines")
    errors.extend(_validate_dq_reconciliation_row(dq_rows))
    return errors


def _validate_workflow_raw(retained: list[dict[str, str]]) -> list[str]:
    parents, errors = _json_payloads_by_kind(retained, "workflow-result")
    children, child_errors = _json_payloads_by_kind(retained, "child-result")
    errors.extend(child_errors)
    statuses = {payload.get("status") for payload in parents}
    child_errors2, child_by_anchor = _validate_workflow_child_rows(children)
    errors.extend(child_errors2)
    parent_errors, parent_ids, repeated_steps = _validate_workflow_parent_rows(
        parents, child_by_anchor
    )
    errors.extend(parent_errors)
    if len(parent_ids) < 2 or not {"success", "failed"}.issubset(statuses):
        errors.append(
            "workflow raw evidence requires distinct success and failure parents"
        )
    for child in children:
        if str(child.get("workflow_run_id") or "") not in parent_ids:
            errors.append("child workflow_run_id must resolve to a retained parent")
    if not _has_repeated_success_and_failure(repeated_steps):
        errors.append(
            "workflow raw evidence requires repeated success/failure runs for one step"
        )
    return errors


_INVENTORY_EMPTY_FIELDS = (
    "recording_declarations_without_output",
    "recording_outputs_without_declaration",
    "policy_aliases_without_catalog",
    "catalog_aliases_without_declaration",
    "policy_aliases_overlapping_outputs",
    "http_semantics_violations",
    "panel_contract_drift",
    "prometheus_run_id_selector_violations",
)
_EXPECTED_TYPED_TARGET_COUNTS = {
    "promql": 171,
    "http": 30,
    "loki": 5,
    "tempo": 0,
    "unknown": 0,
}


def _inventory_report_errors(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    outputs = payload.get("recording_rule_outputs")
    if not isinstance(outputs, list) or len(set(map(str, outputs))) < 103:
        errors.append("inventory must retain at least 103 unique recording outputs")
    for field_name in _INVENTORY_EMPTY_FIELDS:
        if payload.get(field_name) != []:
            errors.append(f"inventory {field_name} must be empty")
    aliases = payload.get("policy_alias_metrics")
    if not isinstance(aliases, list) or len(set(map(str, aliases))) != 20:
        errors.append("inventory must retain exactly 20 governed policy aliases")
    if payload.get("typed_target_counts") != _EXPECTED_TYPED_TARGET_COUNTS:
        errors.append("inventory typed target counts do not match shipped dashboards")
    return errors


def _validate_inventory_raw(retained: list[dict[str, str]]) -> list[str]:
    payloads, errors = _json_payloads_by_kind(retained, "inventory-report")
    if len(payloads) != 1:
        return [*errors, "metric surface requires exactly one inventory report"]
    errors.extend(_inventory_report_errors(payloads[0]))
    return errors


def _dashboard_variable_payload_errors(
    payload: dict[str, object],
    dashboard_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    uid = str(payload.get("dashboard_uid") or "")
    if not uid or uid in dashboard_ids:
        errors.append("dashboard variable reports require unique non-empty UIDs")
    dashboard_ids.add(uid)
    pipelines = payload.get("pipelines")
    exclusion = str(payload.get("eligibility_exclusion") or "").strip()
    if pipelines != list(CHEMBL_PIPELINES) and not exclusion:
        errors.append("dashboard variables require 15 canonical IDs or an exclusion")
    return errors


def _validate_dashboard_raw(retained: list[dict[str, str]]) -> list[str]:
    payloads, errors = _json_payloads_by_kind(retained, "dashboard-variable-report")
    dashboard_ids: set[str] = set()
    for payload in payloads:
        errors.extend(_dashboard_variable_payload_errors(payload, dashboard_ids))
    if len(dashboard_ids) < 8:
        errors.append("dashboard variable evidence requires eight dashboards")
    return errors


def _validate_zero_raw(retained: list[dict[str, str]]) -> list[str]:
    payloads, errors = _json_payloads_by_kind(retained, "raw-zero-source")
    for payload in payloads:
        value = payload.get("value")
        if (
            payload.get("source_present") is not True
            or payload.get("state") != "present"
        ):
            errors.append(
                "numeric zero requires a present raw source and present state"
            )
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value != 0:
            errors.append("raw zero evidence value must be finite numeric zero")
    return errors


def _validate_scrape_raw(retained: list[dict[str, str]]) -> list[str]:
    payloads, errors = _json_payloads_by_kind(retained, "target-capture")
    target_ids: set[str] = set()
    for payload in payloads:
        target_id = str(payload.get("target_id") or "")
        if not target_id or target_id in target_ids:
            errors.append("target captures require unique non-empty target_id values")
        target_ids.add(target_id)
        if payload.get("scrape_interval_elapsed") is not True:
            errors.append("target capture must follow a complete scrape interval")
        if not _parse_generated_at(payload.get("captured_at")):
            errors.append("target capture requires timezone-aware captured_at")
        if payload.get("raw_value") != payload.get("expected_value"):
            errors.append("target raw and independently expected values must match")
    if len(target_ids) < 213:
        errors.append("scrape evidence requires 213 unique executable targets")
    return errors


def _collect_screenshot_hashes(
    retained: list[dict[str, str]],
    errors: list[str],
) -> set[str]:
    """Validate PNG magic and collect retained screenshot hashes."""
    screenshot_hashes: set[str] = set()
    for screenshot in retained:
        if screenshot["kind"] != "screenshot":
            continue
        path = Path(screenshot["path"])
        if not path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            errors.append("retained screenshot must be a PNG artifact")
        screenshot_hashes.add(screenshot["sha256"])
    return screenshot_hashes


def _validate_one_render_manifest(
    payload: dict[str, Any],
    *,
    screenshot_hashes: set[str],
    captures: set[tuple[str, int]],
    stable_windows: set[str],
    errors: list[str],
) -> None:
    """Validate one render-manifest payload and update capture/window sets."""
    uid = str(payload.get("dashboard_uid") or "")
    render_index = payload.get("render_index")
    if not uid or type(render_index) is not int:
        errors.append("render manifest requires dashboard_uid and integer render_index")
        return
    captures.add((uid, render_index))
    stable_windows.add(str(payload.get("stable_window_id") or ""))
    if payload.get("status") != "success":
        errors.append("render manifest status must equal success")
    if payload.get("screenshot_sha256") not in screenshot_hashes:
        errors.append("render manifest screenshot hash must resolve to retained PNG")


def _validate_render_raw(retained: list[dict[str, str]]) -> list[str]:
    manifests, errors = _json_payloads_by_kind(retained, "render-manifest")
    screenshot_hashes = _collect_screenshot_hashes(retained, errors)
    captures: set[tuple[str, int]] = set()
    stable_windows: set[str] = set()
    for payload in manifests:
        _validate_one_render_manifest(
            payload,
            screenshot_hashes=screenshot_hashes,
            captures=captures,
            stable_windows=stable_windows,
            errors=errors,
        )
    dashboards = {uid for uid, _index in captures}
    if len(dashboards) < 8 or len(captures) < 16:
        errors.append("render evidence requires eight dashboards rendered twice")
    if len(stable_windows) != 1 or "" in stable_windows:
        errors.append("all renders must share one non-empty stable monitoring window")
    return errors


def _validate_promtool_raw(retained: list[dict[str, str]]) -> list[str]:
    payloads, errors = _json_payloads_by_kind(retained, "promtool-output")
    phases = {str(payload.get("phase") or "") for payload in payloads}
    expected_phases = {"check-observability", "check-control-plane", "test-fixtures"}
    if phases != expected_phases:
        errors.append(
            "promtool evidence requires both checks and the fixture test phase"
        )
    for payload in payloads:
        if (
            payload.get("tool_version") != "3.13.1"
            or payload.get("exit_code") != 0
            or "SUCCESS" not in str(payload.get("output") or "")
        ):
            errors.append("promtool raw output must prove pinned successful execution")
    return errors


def _validate_online_run_payload(
    runs: list[dict[str, object]],
    expected_binding: dict[str, object] | None,
) -> list[str]:
    """Validate the designated online-run-result payload."""
    if len(runs) != 1:
        return ["online evidence requires exactly one designated run"]
    errors: list[str] = []
    run = runs[0]
    if (
        run.get("status") != "success"
        or run.get("cached_mode") is not False
        or run.get("terminal_event") != "run_finished"
    ):
        errors.append("online run must be successful, uncached, and terminal")
    for field_name in ("run_id", "manifest_id"):
        if not str(run.get(field_name) or "").strip():
            errors.append(f"online run {field_name} must be non-empty")
    if expected_binding is not None and run.get("run_id") != expected_binding.get(
        "online_run_id"
    ):
        errors.append("online raw result does not match the executed online run")
    return errors


def _collect_online_metric_rows(
    instrumentation: list[dict[str, object]],
) -> tuple[dict[str, dict[str, object]], list[str]]:
    """Collapse instrumentation payloads into metric-name keyed rows."""
    metric_rows: dict[str, dict[str, object]] = {}
    errors: list[str] = []
    for payload in instrumentation:
        metrics = payload.get("metrics")
        if (
            not isinstance(metrics, dict)
            or payload.get("raw_source_present") is not True
        ):
            errors.append("online instrumentation requires a present raw metric source")
            continue
        for name, row in metrics.items():
            if isinstance(row, dict):
                metric_rows[str(name)] = row
    return metric_rows, errors


def _validate_online_metric_deltas(
    metric_rows: dict[str, dict[str, object]],
) -> list[str]:
    """Require governed online metric deltas and the controlled retry probe."""
    required_deltas = {
        "bioetl_adapter_requests_total": 1,
        "bioetl_rate_limiter_wait_seconds_count": 1,
        "bioetl_circuit_breaker_success_total": 1,
        "bioetl_adapter_request_duration_seconds_count": 1,
    }
    errors: list[str] = []
    for metric_name, minimum_delta in required_deltas.items():
        row = metric_rows.get(metric_name, {})
        if row.get("source_present") is not True:
            errors.append(f"online metric {metric_name} requires a present raw source")
        delta = row.get("delta")
        if (
            not isinstance(delta, (int, float))
            or isinstance(delta, bool)
            or delta < minimum_delta
        ):
            errors.append(
                f"online metric {metric_name} delta must be >= {minimum_delta}"
            )
    retry_row = metric_rows.get("bioetl_data_source_retries_total", {})
    if retry_row.get("source_present") is not True or retry_row.get("delta") != 1:
        errors.append(
            "controlled online retry probe must increment retry metric exactly once"
        )
    return errors


def _validate_online_raw(
    retained: list[dict[str, str]],
    expected_binding: dict[str, object] | None = None,
) -> list[str]:
    runs, errors = _json_payloads_by_kind(retained, "online-run-result")
    instrumentation, metric_errors = _json_payloads_by_kind(
        retained, "instrumentation-response"
    )
    errors.extend(metric_errors)
    errors.extend(_validate_online_run_payload(runs, expected_binding))
    metric_rows, instrumentation_errors = _collect_online_metric_rows(instrumentation)
    errors.extend(instrumentation_errors)
    errors.extend(_validate_online_metric_deltas(metric_rows))
    return errors


def _backend_http_profile_errors(http_rows: list[dict[str, Any]]) -> list[str]:
    if len(http_rows) != 1:
        return ["backend profile requires exactly one retained HTTP response"]
    row = http_rows[0]
    if (
        row.get("state") != "populated"
        or row.get("read_only_mount") is not True
        or not str(row.get("data_root") or "").strip()
        or int(row.get("record_count", 0)) < 1
    ):
        return ["backend HTTP response must prove the exact populated read-only root"]
    return []


def _backend_loki_profile_errors(loki_rows: list[dict[str, Any]]) -> list[str]:
    if len(loki_rows) != 1:
        return ["backend profile requires exactly one retained Loki response"]
    row = loki_rows[0]
    if (
        row.get("job") != "bioetl-audit"
        or row.get("sentinel_match_count") != 1
        or row.get("read_only_mount") is not True
        or not str(row.get("log_root") or "").strip()
    ):
        return ["Loki response must prove one bounded bioetl-audit sentinel"]
    return []


def _backend_signature_errors(signatures: list[dict[str, Any]]) -> list[str]:
    if len(signatures) != 1:
        return ["backend profile requires one canonical before/after signature"]
    row = signatures[0]
    if row.get("before") != row.get("after") or row.get("unchanged") is not True:
        return ["canonical data/log signatures must remain unchanged"]
    return []


def _validate_backend_profile_raw(retained: list[dict[str, str]]) -> list[str]:
    http_rows, errors = _json_payloads_by_kind(retained, "backend-http-response")
    loki_rows, loki_errors = _json_payloads_by_kind(retained, "loki-response")
    signatures, signature_errors = _json_payloads_by_kind(
        retained, "canonical-signature"
    )
    errors.extend(loki_errors)
    errors.extend(signature_errors)
    errors.extend(_backend_http_profile_errors(http_rows))
    errors.extend(_backend_loki_profile_errors(loki_rows))
    errors.extend(_backend_signature_errors(signatures))
    return errors


def _validate_raw_content(
    key: str,
    retained: list[dict[str, str]],
    expected_binding: dict[str, object] | None = None,
) -> list[str]:
    validators = {
        "tracing_parity": _validate_tracing_raw,
        "metric_reconciliation": _validate_metric_reconciliation_raw,
        "workflow_correlation": _validate_workflow_raw,
        "metric_surface": _validate_inventory_raw,
        "dashboard_variables": _validate_dashboard_raw,
        "zero_evidence": _validate_zero_raw,
        "scrape_targets": _validate_scrape_raw,
        "render_stability": _validate_render_raw,
        "promtool": _validate_promtool_raw,
        "online_run": _validate_online_raw,
        "backend_profile": _validate_backend_profile_raw,
    }
    if key == "tracing_parity":
        return _validate_tracing_raw(retained, expected_binding)
    if key == "online_run":
        return _validate_online_raw(retained, expected_binding)
    return validators[key](retained)


def _evidence_path_uniqueness_errors(evidence: dict[str, str]) -> list[str]:
    """Return errors when evidence artifacts reuse the same path."""
    resolved_paths = [Path(value).resolve() for value in evidence.values()]
    if len(set(resolved_paths)) != len(resolved_paths):
        return ["each evidence type requires a unique artifact"]
    return []


def _gate_one_evidence_key(
    key: str,
    raw_path: str | None,
    *,
    evidence_root: Path,
    raw_root: Path,
    source_revision: str,
    expected_binding: dict[str, object] | None,
) -> tuple[
    list[str], dict[str, str] | None, dict[str, int] | None, list[dict[str, str]]
]:
    """Validate one required external evidence artifact."""
    if raw_path is None:
        return ["missing evidence artifact"], None, None, []
    path = Path(raw_path).resolve()
    key_errors: list[str] = []
    if evidence_root not in path.parents:
        key_errors.append("artifact must be inside AUDIT_ROOT/evidence")
    if not path.is_file():
        key_errors.append("artifact is not a file")
        return key_errors, None, None, []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid JSON: {exc}"], None, None, []
    summary: dict[str, int] | None = None
    retained: list[dict[str, str]] = []
    if not isinstance(payload, dict):
        key_errors.append("payload must be an object")
    else:
        field_errors, parsed_summary, retained = _validate_evidence_object_fields(
            key,
            payload,
            source_revision=source_revision,
            expected_binding=expected_binding,
            raw_root=raw_root,
        )
        key_errors.extend(field_errors)
        if parsed_summary:
            summary = parsed_summary
    artifact = {"path": str(path), "sha256": _sha256_file(path)}
    return key_errors, artifact, summary, retained


def _evidence_gate(
    evidence: dict[str, str],
    *,
    audit_root: Path,
    source_revision: str,
    expected_binding: dict[str, object] | None = None,
) -> dict[str, object]:
    errors: dict[str, list[str]] = {}
    evidence_root = (audit_root / "evidence").resolve()
    path_errors = _evidence_path_uniqueness_errors(evidence)
    if path_errors:
        errors["_paths"] = path_errors
    unexpected_keys = sorted(set(evidence) - set(REQUIRED_EXTERNAL_EVIDENCE))
    if unexpected_keys:
        errors["_keys"] = ["unexpected evidence types: " + ", ".join(unexpected_keys)]
    artifacts: dict[str, dict[str, str]] = {}
    raw_artifacts_retained: dict[str, list[dict[str, str]]] = {}
    summaries: dict[str, dict[str, int]] = {}
    raw_root = (evidence_root / "raw").resolve()
    for key in REQUIRED_EXTERNAL_EVIDENCE:
        key_errors, artifact, summary, retained = _gate_one_evidence_key(
            key,
            evidence.get(key),
            evidence_root=evidence_root,
            raw_root=raw_root,
            source_revision=source_revision,
            expected_binding=expected_binding,
        )
        if key_errors:
            errors[key] = key_errors
        if artifact is not None:
            artifacts[key] = artifact
            raw_artifacts_retained[key] = retained
        if summary is not None:
            summaries[key] = summary
    return {
        "satisfied": not errors,
        "errors": errors,
        "artifacts": artifacts,
        "raw_artifacts": raw_artifacts_retained,
        "summaries": summaries,
    }


def _scorecard(external_gate: dict[str, object]) -> dict[str, dict[str, float]]:
    summaries = external_gate.get("summaries")
    typed = summaries if isinstance(summaries, dict) else {}
    score_fields = {
        "dashboard_quality": ("render_stability", "dashboard_quality_score_x100", 4232),
        "metric_quality": ("metric_surface", "metric_quality_score_x100", 4600),
        "chembl_population": (
            "tracing_parity",
            "chembl_population_score_x100",
            4321,
        ),
        "overall_observability": (
            "online_run",
            "overall_observability_score_x100",
            4600,
        ),
    }
    scorecard: dict[str, dict[str, float]] = {}
    for name, (category, field_name, baseline_x100) in score_fields.items():
        category_summary = typed.get(category)
        current_x100 = (
            category_summary.get(field_name)
            if isinstance(category_summary, dict)
            else None
        )
        current = float(current_x100) / 100 if type(current_x100) is int else 0.0
        baseline = baseline_x100 / 100
        scorecard[name] = {
            "baseline": baseline,
            "current": current,
            "delta": round(current - baseline, 2),
        }
    return scorecard


def _residual_findings_gate(
    limitations: list[str], finding_specs: list[str]
) -> dict[str, object]:
    errors: list[str] = []
    mappings: list[dict[str, str]] = []
    if len(limitations) != len(finding_specs):
        errors.append("each residual limitation requires exactly one finding issue")
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for index, limitation in enumerate(limitations):
        if not limitation.strip():
            errors.append(f"residual limitation {index} must be non-empty")
        if index >= len(finding_specs):
            continue
        finding_id, separator, issue_url = finding_specs[index].partition("=")
        if not separator or not re.fullmatch(r"[A-Z][A-Z0-9-]+-\d{3}", finding_id):
            errors.append(f"finding {index} must use FINDING-ID=https://.../issues/N")
            continue
        if not re.fullmatch(
            r"https://github\.com/SatoryKono/BioactivityDataAcquisition/issues/\d+",
            issue_url,
        ):
            errors.append(f"finding {index} must reference a BioETL GitHub issue URL")
            continue
        if finding_id in seen_ids or issue_url in seen_urls:
            errors.append("finding IDs and issue URLs must be unique")
        seen_ids.add(finding_id)
        seen_urls.add(issue_url)
        mappings.append(
            {
                "limitation": limitation,
                "finding_id": finding_id,
                "issue_url": issue_url,
            }
        )
    if limitations:
        errors.append(
            "residual limitations must be resolved before campaign completion"
        )
    return {"satisfied": not errors, "errors": errors, "mappings": mappings}


def _stable_sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


def _campaign_binding(
    *,
    source_provenance: dict[str, object],
    attempts: list[AttemptEvidence],
    online_attempt: AttemptEvidence,
    phases: tuple[PhaseEvidence, ...],
) -> dict[str, object]:
    """Bind external observations to one immutable execution occurrence."""
    standalone = [
        {
            "pipeline": attempt.pipeline,
            "tracing": attempt.tracing,
            "run_ids": list(attempt.run_ids),
            "result_signature": attempt.result_signature,
        }
        for attempt in sorted(attempts, key=lambda item: (item.pipeline, item.tracing))
    ]
    phase_payload = [
        {
            "name": phase.name,
            "command": list(phase.command),
            "stdout_sha256": phase.stdout_sha256,
            "stderr_sha256": phase.stderr_sha256,
        }
        for phase in phases
    ]
    return {
        "source_revision": source_provenance["revision"],
        "source_tree": source_provenance["tree"],
        "standalone_attempts_sha256": _stable_sha256(standalone),
        "standalone_attempts": standalone,
        "online_run_id": online_attempt.run_ids[0]
        if len(online_attempt.run_ids) == 1
        else "",
        "phase_evidence_sha256": _stable_sha256(phase_payload),
    }


def _retained_artifacts_valid(report: dict[str, object]) -> tuple[bool, list[str]]:
    """Re-hash execution artifacts before accepting separately produced evidence."""
    errors: list[str] = []
    errors.extend(_validate_attempt_artifacts(report.get("attempts")))
    workflow_gate = report.get("workflow_phase_gate")
    phases = workflow_gate.get("phases") if isinstance(workflow_gate, dict) else None
    errors.extend(_validate_workflow_phase_stream_artifacts(phases))
    return not errors, errors


def _load_finalize_report(
    *,
    report_path: Path,
    audit_root: Path,
    source_provenance: dict[str, object],
) -> dict[str, object]:
    """Load and validate the awaiting-evidence campaign report for finalization."""
    expected_report_path = (
        audit_root / OBSERVABILITY_CLOSURE_CAMPAIGN_REPORT
    ).resolve()
    if report_path != expected_report_path or not report_path.is_file():
        raise ValueError(
            "--finalize-report must name AUDIT_ROOT/"
            f"{OBSERVABILITY_CLOSURE_CAMPAIGN_REPORT}"
        )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("campaign report must be a schema_version=1 object")
    if payload.get("status") != "awaiting_external_evidence":
        raise ValueError("campaign report is not awaiting external evidence")
    if payload.get("source_revision") != source_provenance["revision"]:
        raise ValueError("campaign report source revision no longer matches HEAD")
    report_provenance = payload.get("source_provenance")
    if not isinstance(report_provenance, dict) or report_provenance.get(
        "tree"
    ) != source_provenance.get("tree"):
        raise ValueError("campaign report source tree no longer matches HEAD")
    if not isinstance(payload.get("campaign_binding"), dict):
        raise ValueError("campaign report has no occurrence binding")
    return payload


def _core_campaign_gates_satisfied(payload: dict[str, object]) -> bool:
    """Return whether execute-time campaign gates remain satisfied."""
    gate_fields = (
        "attempt_gate",
        "online_attempt_gate",
        "workflow_phase_gate",
        "canonical_signature_gate",
    )
    if payload.get("pipeline_config_parity") is not True:
        return False
    for field_name in gate_fields:
        gate = payload.get(field_name)
        if not isinstance(gate, dict) or gate.get("satisfied") is not True:
            return False
    return True
