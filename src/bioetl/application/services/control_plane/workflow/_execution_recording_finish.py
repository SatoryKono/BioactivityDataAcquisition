"""Workflow finished success/failure ledger updates."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import cast

from bioetl.application.services.control_plane.workflow.execution_recording_context import (
    WorkflowExecutionRecorder,
)
from bioetl.application.services.control_plane.workflow.execution_recording_payloads import (
    _find_failed_step,
    _workflow_failure_message,
)
from bioetl.application.services.workflow.workflow_runner_service import (
    WorkflowRunExecutionResult,
)

_UNSET_CURSOR = object()


def _record_workflow_success(
    context: WorkflowExecutionRecorder,
    *,
    completed_at: datetime,
    summary: dict[str, object],
    last_start_offset: int | object | None = _UNSET_CURSOR,
    last_limit: int | object | None = _UNSET_CURSOR,
) -> None:
    entry = context.ledger.record_workflow_finished(details=summary)
    resolved_start_offset = context.state.last_start_offset
    if last_start_offset is not _UNSET_CURSOR:
        resolved_start_offset = cast("int | None", last_start_offset)
    resolved_limit = context.state.last_limit
    if last_limit is not _UNSET_CURSOR:
        resolved_limit = cast("int | None", last_limit)
    context.state = replace(
        context.state,
        status="success",
        updated_at=entry.occurred_at,
        completed_at=completed_at,
        last_event_id=entry.entry_id,
        last_error_type=None,
        last_error_message=None,
        last_start_offset=resolved_start_offset,
        last_limit=resolved_limit,
    )
    context.state_port.save(context.state)


def _record_workflow_failure(
    context: WorkflowExecutionRecorder,
    *,
    result: WorkflowRunExecutionResult,
    completed_at: datetime,
    summary: dict[str, object],
) -> None:
    failed_step = _find_failed_step(result)
    entry = context.ledger.record_workflow_failed(
        message=_workflow_failure_message(failed_step),
        error_type=None if failed_step is None else failed_step.error_type,
        details=summary,
    )
    context.state = replace(
        context.state,
        status="failed",
        updated_at=entry.occurred_at,
        completed_at=completed_at,
        last_event_id=entry.entry_id,
        last_error_type=None if failed_step is None else failed_step.error_type,
        last_error_message=None if failed_step is None else failed_step.error_message,
    )
    context.state_port.save(context.state)
