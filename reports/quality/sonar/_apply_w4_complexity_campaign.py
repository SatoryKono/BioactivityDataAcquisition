"""W4: extract helpers to cut cognitive complexity in observability campaign."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "scripts/engineering/qa/run_observability_closure_campaign.py"

HELPERS = r'''

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
        errors.append(
            f"raw_artifacts[{index}] must be inside AUDIT_ROOT/evidence/raw"
        )
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


def _validate_workflow_child_rows(
    children: list[dict[str, object]],
) -> tuple[list[str], dict[tuple[str, str], dict[str, object]]]:
    errors: list[str] = []
    child_by_anchor: dict[tuple[str, str], dict[str, object]] = {}
    for child in children:
        for field_name in (
            "workflow_run_id",
            "run_id",
            "manifest_id",
            "workflow_name",
            "workflow_step_id",
        ):
            if not str(child.get(field_name) or "").strip():
                errors.append(f"child {field_name} must be non-empty")
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
    return errors, child_by_anchor


def _validate_workflow_parent_rows(
    parents: list[dict[str, object]],
    child_by_anchor: dict[tuple[str, str], dict[str, object]],
) -> tuple[list[str], set[str], dict[tuple[str, str], list[dict[str, object]]]]:
    errors: list[str] = []
    parent_ids: set[str] = set()
    repeated_steps: dict[tuple[str, str], list[dict[str, object]]] = {}
    for parent in parents:
        for field_name in (
            "workflow_run_id",
            "workflow_name",
            "workflow_step_id",
            "child_run_id",
            "child_manifest_id",
        ):
            if not str(parent.get(field_name) or "").strip():
                errors.append(f"parent {field_name} must be non-empty")
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
            continue
        for field_name in (
            "workflow_run_id",
            "workflow_name",
            "workflow_step_id",
        ):
            if str(child.get(field_name) or "") != str(parent.get(field_name) or ""):
                errors.append(
                    f"parent/child {field_name} must match for reciprocal anchors"
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
    if isinstance(payload.get("summary"), dict):
        summaries = {
            str(field): value
            for field, value in payload["summary"].items()
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
            artifacts = attempt.get(field_name)
            if not isinstance(artifacts, list):
                errors.append(
                    f"attempts[{attempt_index}].{field_name} must be an array"
                )
                continue
            for artifact_index, artifact in enumerate(artifacts):
                label = f"attempts[{attempt_index}].{field_name}[{artifact_index}]"
                if not isinstance(artifact, dict):
                    errors.append(f"{label} must be an object")
                    continue
                path = Path(str(artifact.get("path") or ""))
                expected = str(artifact.get("sha256") or "")
                if not path.is_file():
                    errors.append(f"{label} is missing")
                elif _sha256_file(path) != expected:
                    errors.append(f"{label} hash changed after execution")
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


'''


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    marker = "def _validate_raw_artifacts("
    if marker not in text:
        raise SystemExit("marker missing")
    if "_validate_one_raw_artifact(" not in text:
        text = text.replace(marker, HELPERS + marker, 1)
        print("inserted helpers")
    else:
        print("helpers already present")

    replacements: list[tuple[str, str, str]] = []

    replacements.append(
        (
            "raw",
            '''def _validate_raw_artifacts(
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
        if not isinstance(artifact, dict):
            errors.append(f"raw_artifacts[{index}] must be an object")
            continue
        path = Path(str(artifact.get("path") or "")).expanduser().resolve()
        kind = str(artifact.get("kind") or "").strip()
        expected_sha256 = str(artifact.get("sha256") or "").strip()
        if raw_root not in path.parents:
            errors.append(
                f"raw_artifacts[{index}] must be inside AUDIT_ROOT/evidence/raw"
            )
        if path in seen_paths:
            errors.append(f"raw_artifacts[{index}] duplicates another raw artifact")
        seen_paths.add(path)
        if not path.is_file():
            errors.append(f"raw_artifacts[{index}] is not a file")
            continue
        actual_sha256 = _sha256_file(path)
        if expected_sha256 != actual_sha256:
            errors.append(f"raw_artifacts[{index}].sha256 does not match content")
        if not kind:
            errors.append(f"raw_artifacts[{index}].kind must be non-empty")
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        retained.append({"path": str(path), "sha256": actual_sha256, "kind": kind})
    for kind, minimum in EVIDENCE_RAW_KIND_REQUIREMENTS[key].items():
        if kind_counts.get(kind, 0) < minimum:
            errors.append(f"raw artifact kind {kind!r} requires at least {minimum}")
    return errors, retained
''',
            '''def _validate_raw_artifacts(
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
''',
        )
    )

    # Load remaining replacements from companion data file to keep this script shorter
    data_path = Path(__file__).with_name("_apply_w4_complexity_campaign_bodies.py")
    # Inline critical remaining replacements below via exec of second half
    from importlib.util import module_from_spec, spec_from_file_location

    bodies_path = Path(__file__).with_name("_w4_campaign_replacements.py")
    if bodies_path.exists():
        ns: dict[str, object] = {}
        exec(bodies_path.read_text(encoding="utf-8"), ns)
        extra = ns.get("REPLACEMENTS")
        if isinstance(extra, list):
            replacements.extend(extra)  # type: ignore[arg-type]

    for name, old, new in replacements:
        if old not in text:
            if new.strip() in text:
                print(f"skip {name}: already applied")
                continue
            raise SystemExit(f"missing block: {name}")
        text = text.replace(old, new, 1)
        print(f"replaced {name}")

    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print("wrote", TARGET)


if __name__ == "__main__":
    main()
