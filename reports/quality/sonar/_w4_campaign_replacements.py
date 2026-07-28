# Additional (old, new) replacement blocks for W4 campaign complexity extract.
# Each item: (name, old, new)

REPLACEMENTS: list[tuple[str, str, str]] = [
    (
        "metric",
        '''def _validate_metric_reconciliation_raw(
    retained: list[dict[str, str]],
) -> list[str]:
    prometheus, errors = _json_payloads_by_kind(retained, "prometheus-response")
    ledgers, ledger_errors = _json_payloads_by_kind(retained, "ledger-snapshot")
    dq_rows, dq_errors = _json_payloads_by_kind(retained, "dq-anomaly-response")
    errors.extend(ledger_errors)
    errors.extend(dq_errors)
    if len(prometheus) != 15 or len(ledgers) != 15:
        errors.append("metric reconciliation requires 15 Prometheus and 15 ledger rows")
    prom_by_key: dict[tuple[str, str], dict[str, object]] = {}
    ledger_by_key: dict[tuple[str, str], dict[str, object]] = {}
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
    if set(prom_by_key) != set(ledger_by_key):
        errors.append("Prometheus and ledger pipeline/run anchors must match exactly")
    if {pipeline for pipeline, _run_id in prom_by_key} != set(CHEMBL_PIPELINES):
        errors.append("metric reconciliation must cover all 15 canonical pipelines")
    if len(dq_rows) != 1:
        errors.append("metric reconciliation requires one focused DQ anomaly row")
    else:
        dq_row = dq_rows[0]
        if (
            dq_row.get("source_present") is not True
            or dq_row.get("metric") != "bioetl_dq_anomaly_detected"
            or dq_row.get("delta") != 1
            or not str(dq_row.get("test_node_id") or "").strip()
        ):
            errors.append(
                "focused DQ failure must increment one present anomaly metric"
            )
    return errors
''',
        '''def _validate_metric_reconciliation_raw(
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
''',
    ),
    (
        "workflow",
        '''def _validate_workflow_raw(retained: list[dict[str, str]]) -> list[str]:
    parents, errors = _json_payloads_by_kind(retained, "workflow-result")
    children, child_errors = _json_payloads_by_kind(retained, "child-result")
    errors.extend(child_errors)
    parent_ids: set[str] = set()
    statuses = {payload.get("status") for payload in parents}
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

    if len(parent_ids) < 2 or not {"success", "failed"}.issubset(statuses):
        errors.append(
            "workflow raw evidence requires distinct success and failure parents"
        )
    for child in children:
        if str(child.get("workflow_run_id") or "") not in parent_ids:
            errors.append("child workflow_run_id must resolve to a retained parent")
    has_repeated_success_and_failure = any(
        len(
            {
                str(parent.get("workflow_run_id") or "")
                for parent in occurrences
                if str(parent.get("workflow_run_id") or "")
            }
        )
        >= 2
        and {"success", "failed"}.issubset(
            {parent.get("status") for parent in occurrences}
        )
        for (workflow_name, workflow_step_id), occurrences in repeated_steps.items()
        if workflow_name and workflow_step_id
    )
    if not has_repeated_success_and_failure:
        errors.append(
            "workflow raw evidence requires repeated success/failure runs for one step"
        )
    return errors
''',
        '''def _validate_workflow_raw(retained: list[dict[str, str]]) -> list[str]:
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
''',
    ),
    (
        "evidence_loop",
        '''    for key in REQUIRED_EXTERNAL_EVIDENCE:
        key_errors: list[str] = []
        raw_path = evidence.get(key)
        if raw_path is None:
            errors[key] = ["missing evidence artifact"]
            continue
        path = Path(raw_path).resolve()
        if evidence_root not in path.parents:
            key_errors.append("artifact must be inside AUDIT_ROOT/evidence")
        if not path.is_file():
            key_errors.append("artifact is not a file")
            errors[key] = key_errors
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors[key] = [f"invalid JSON: {exc}"]
            continue
        if not isinstance(payload, dict):
            key_errors.append("payload must be an object")
        else:
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
                key_errors.append(
                    "campaign_binding does not match the executed campaign"
                )
            if not _parse_generated_at(payload.get("generated_at")):
                key_errors.append("generated_at must be timezone-aware ISO-8601")
            key_errors.extend(_validate_summary(key, payload.get("summary")))
            if isinstance(payload.get("summary"), dict):
                summaries[key] = {
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
                key_errors.extend(
                    _validate_raw_content(key, retained, expected_binding)
                )
            raw_artifacts_retained[key] = retained
        if key_errors:
            errors[key] = key_errors
        artifacts[key] = {"path": str(path), "sha256": _sha256_file(path)}
''',
        '''    for key in REQUIRED_EXTERNAL_EVIDENCE:
        raw_path = evidence.get(key)
        if raw_path is None:
            errors[key] = ["missing evidence artifact"]
            continue
        path = Path(raw_path).resolve()
        key_errors: list[str] = []
        if evidence_root not in path.parents:
            key_errors.append("artifact must be inside AUDIT_ROOT/evidence")
        if not path.is_file():
            key_errors.append("artifact is not a file")
            errors[key] = key_errors
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors[key] = [f"invalid JSON: {exc}"]
            continue
        if not isinstance(payload, dict):
            key_errors.append("payload must be an object")
        else:
            field_errors, summary, retained = _validate_evidence_object_fields(
                key,
                payload,
                source_revision=source_revision,
                expected_binding=expected_binding,
                raw_root=raw_root,
            )
            key_errors.extend(field_errors)
            if summary:
                summaries[key] = summary
            raw_artifacts_retained[key] = retained
        if key_errors:
            errors[key] = key_errors
        artifacts[key] = {"path": str(path), "sha256": _sha256_file(path)}
''',
    ),
    (
        "retained",
        '''def _retained_artifacts_valid(report: dict[str, object]) -> tuple[bool, list[str]]:
    """Re-hash execution artifacts before accepting separately produced evidence."""
    errors: list[str] = []

    def validate_artifact(artifact: object, label: str) -> None:
        if not isinstance(artifact, dict):
            errors.append(f"{label} must be an object")
            return
        path = Path(str(artifact.get("path") or ""))
        expected = str(artifact.get("sha256") or "")
        if not path.is_file():
            errors.append(f"{label} is missing")
        elif _sha256_file(path) != expected:
            errors.append(f"{label} hash changed after execution")

    attempts = report.get("attempts")
    if not isinstance(attempts, list) or not attempts:
        errors.append("attempts must be a non-empty array")
    else:
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
                    validate_artifact(
                        artifact,
                        f"attempts[{attempt_index}].{field_name}[{artifact_index}]",
                    )
    workflow_gate = report.get("workflow_phase_gate")
    phases = workflow_gate.get("phases") if isinstance(workflow_gate, dict) else None
    if not isinstance(phases, list) or not phases:
        errors.append("workflow phase evidence is missing")
    else:
        for phase_index, phase in enumerate(phases):
            if not isinstance(phase, dict):
                errors.append(f"workflow phase {phase_index} must be an object")
                continue
            for stream_name in ("stdout", "stderr"):
                validate_artifact(
                    {
                        "path": phase.get(f"{stream_name}_path"),
                        "sha256": phase.get(f"{stream_name}_sha256"),
                    },
                    f"workflow phase {phase_index} {stream_name}",
                )
    return not errors, errors
''',
        '''def _retained_artifacts_valid(report: dict[str, object]) -> tuple[bool, list[str]]:
    """Re-hash execution artifacts before accepting separately produced evidence."""
    errors: list[str] = []
    errors.extend(_validate_attempt_artifacts(report.get("attempts")))
    workflow_gate = report.get("workflow_phase_gate")
    phases = workflow_gate.get("phases") if isinstance(workflow_gate, dict) else None
    errors.extend(_validate_workflow_phase_stream_artifacts(phases))
    return not errors, errors
''',
    ),
]
