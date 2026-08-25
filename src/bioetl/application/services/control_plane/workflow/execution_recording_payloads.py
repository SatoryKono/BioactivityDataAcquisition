"""Payload helpers for workflow execution recording."""

from __future__ import annotations

from bioetl.application.services.workflow.workflow_runner_service import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
)

_TRANSFORM_RESULT_SUMMARY_KEYS = (
    "transform_name",
    "workflow_name",
    "workflow_run_id",
    "manifest_id",
    "step_id",
    "source_table",
    "reference_table",
    "source_key",
    "reference_key",
    "source_layer",
    "reference_layer",
    "mutation_layer",
    "source_keys",
    "reference_keys",
    "action",
    "nulls_equal",
    "scanned_rows",
    "retained_rows",
    "orphan_rows_deleted",
    "mutated",
    "dry_run",
    "would_mutate",
    "mutation_mode",
    "quarantine_batch_id",
    "quarantine_rows_written",
    "quarantine_error_code",
    "mutation_blocked_reason",
)


def _fingerprint_details(fingerprint: str | None) -> dict[str, object] | None:
    return {"fingerprint": fingerprint} if fingerprint is not None else None


def build_step_completion_details(
    result: WorkflowStepExecutionResult,
) -> dict[str, object] | None:
    """Build compact workflow-step completion details for ledger persistence."""
    fingerprint = _resolve_result_fingerprint(result)
    if result.step_kind == "pipeline":
        return _pipeline_child_details(result, fingerprint=fingerprint)
    if result.status != "success":
        return _fingerprint_details(fingerprint)
    payload = result.payload
    output = (
        payload.get("output")
        if isinstance(payload, dict)
        else getattr(payload, "output", None)
    )
    if not isinstance(output, dict):
        return _fingerprint_details(fingerprint)
    details: dict[str, object] = {}
    if fingerprint is not None:
        details["fingerprint"] = fingerprint
    summary = _transform_result_summary(output)
    if summary:
        details["transform_result_summary"] = summary
    artifact_refs = _artifact_refs(output)
    if artifact_refs is not None:
        details["artifacts"] = artifact_refs
    return details or None


def _pipeline_child_id(
    result: WorkflowStepExecutionResult,
    *,
    direct_field: str,
    payload_field: str,
) -> str | None:
    """Resolve one reciprocal child identifier from the step result."""
    value = getattr(result, direct_field, None)
    if value is None:
        payload = result.payload
        value = (
            payload.get(payload_field)
            if isinstance(payload, dict)
            else getattr(payload, payload_field, None)
        )
    return None if value is None else str(value)


def _pipeline_child_details(
    result: WorkflowStepExecutionResult,
    *,
    fingerprint: str | None,
) -> dict[str, object] | None:
    """Return reciprocal child-run anchors for a terminal pipeline step."""
    child_run_id = _pipeline_child_id(
        result,
        direct_field="child_run_id",
        payload_field="run_id",
    )
    child_manifest_id = _pipeline_child_id(
        result,
        direct_field="child_manifest_id",
        payload_field="manifest_id",
    )
    if child_run_id is None or child_manifest_id is None:
        return None
    details: dict[str, object] = {
        "child_run_id": child_run_id,
        "child_manifest_id": child_manifest_id,
    }
    if fingerprint is not None:
        details["fingerprint"] = fingerprint
    return details


def _transform_result_summary(output: dict[str, object]) -> dict[str, object]:
    return {
        key: output[key]
        for key in _TRANSFORM_RESULT_SUMMARY_KEYS
        if key in output and output[key] is not None
    }


def _artifact_refs(output: dict[str, object]) -> list[dict[str, object]] | None:
    artifact_refs = output.get("artifact_refs")
    if not isinstance(artifact_refs, list):
        return None
    return [dict(item) for item in artifact_refs if isinstance(item, dict)]


def _resolve_result_fingerprint(result: WorkflowStepExecutionResult) -> str | None:
    payload = result.payload
    fingerprint = getattr(payload, "fingerprint", None)
    if fingerprint is not None:
        return str(fingerprint)
    if isinstance(payload, dict):
        dict_fingerprint = payload.get("fingerprint")
        if dict_fingerprint is not None:
            return str(dict_fingerprint)
    return None


def _build_result_summary(result: WorkflowRunExecutionResult) -> dict[str, object]:
    counts = {"success": 0, "failed": 0, "skipped": 0}
    for step in result.steps:
        if step.status in counts:
            counts[step.status] += 1
    return {"status": result.status, "step_counts": counts}


__all__ = [
    "_build_result_summary",
    "_fingerprint_details",
    "_resolve_result_fingerprint",
    "build_step_completion_details",
]
