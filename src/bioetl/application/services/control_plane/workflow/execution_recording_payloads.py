"""Payload helpers for workflow execution recording."""

from __future__ import annotations

from bioetl.application.services.workflow_runner_service import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
)


def _fingerprint_details(fingerprint: str | None) -> dict[str, str] | None:
    return {"fingerprint": fingerprint} if fingerprint is not None else None


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


def _find_failed_step(
    result: WorkflowRunExecutionResult,
) -> WorkflowStepExecutionResult | None:
    for step in result.steps:
        if step.status == "failed":
            return step
    return None


def _workflow_failure_message(
    failed_step: WorkflowStepExecutionResult | None,
) -> str:
    if failed_step is not None and failed_step.error_message:
        return failed_step.error_message
    return "Workflow execution failed"


__all__ = [
    "_build_result_summary",
    "_find_failed_step",
    "_fingerprint_details",
    "_resolve_result_fingerprint",
    "_workflow_failure_message",
]
