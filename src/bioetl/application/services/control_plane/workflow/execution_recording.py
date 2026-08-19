"""Workflow execution ledger/state recording helpers."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import cast

from bioetl.application.services.control_plane.workflow.execution_recording_context import (
    WorkflowExecutionRecorder,
)
from bioetl.application.services.control_plane.workflow.execution_recording_payloads import (
    _build_result_summary,
    _find_failed_step,
    _fingerprint_details,
    _resolve_result_fingerprint,
    _workflow_failure_message,
    build_step_completion_details,
)
from bioetl.application.services.control_plane.workflow.execution_recording_state import (
    _apply_completed_step_state,
    _clear_ambiguous_step,
    _find_step_state,
    _record_completed_transform_fingerprint,
    _record_step_state,
    _remove_step_ids,
)
from bioetl.application.services.workflow.workflow_runner_service import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
    WorkflowTransformDestructiveCommit,
)
from bioetl.domain.control_plane import WorkflowStepState
from bioetl.domain.workflow import TransformStepConfig, WorkflowStepConfig

_UNSET_CURSOR = object()

__all__ = [
    "WorkflowExecutionRecorder",
    "record_step_completed",
    "record_step_started",
    "record_transform_commit",
    "record_workflow_finished",
    "record_workflow_started",
]


def record_workflow_started(
    context: WorkflowExecutionRecorder,
    *,
    resumed: bool,
    repair_steps: tuple[str, ...],
    force_steps: tuple[str, ...],
) -> None:
    """Record start events and persist the running workflow state."""
    if repair_steps:
        context.ledger.record_repair_requested(step_ids=repair_steps)
    if force_steps:
        context.ledger.record_force_requested(step_ids=force_steps)
    started_entry = context.ledger.record_workflow_started(resumed=resumed)
    context.state = replace(
        context.state,
        status="running",
        updated_at=started_entry.occurred_at,
        last_event_id=started_entry.entry_id,
        repair_required=False,
        repair_hint=None,
        ambiguous_step_ids=_remove_step_ids(
            context.state.ambiguous_step_ids,
            repair_steps,
        ),
    )
    context.state_port.save(context.state)


def record_step_started(
    context: WorkflowExecutionRecorder,
    step: TransformStepConfig | WorkflowStepConfig,
    *,
    fingerprint: str | None = None,
) -> None:
    """Record one workflow step start in ledger and durable state."""
    step_id = step.step_id
    step_kind = "transform" if isinstance(step, TransformStepConfig) else "pipeline"
    entry = context.ledger.record_step_started(
        step_id=step_id,
        step_kind=step_kind,
        details=_fingerprint_details(fingerprint),
    )
    context.state = _record_step_state(
        context.state,
        WorkflowStepState(
            step_id=step_id,
            step_kind=step_kind,
            status="running",
            fingerprint=fingerprint,
        ),
        updated_at=entry.occurred_at,
        last_event_id=entry.entry_id,
    )
    context.state_port.save(context.state)


def record_step_completed(
    context: WorkflowExecutionRecorder,
    result: WorkflowStepExecutionResult,
) -> None:
    """Record one workflow step terminal state."""
    fingerprint = _resolve_result_fingerprint(result)
    entry = context.ledger.record_step_completed(
        step_id=result.step_id,
        step_kind=result.step_kind,
        status=result.status,
        message=result.error_message,
        error_type=result.error_type,
        details=build_step_completion_details(result),
    )
    if result.error_type == "AlreadyCompletedOnResume":
        context.state = replace(
            context.state,
            updated_at=entry.occurred_at,
            last_event_id=entry.entry_id,
        )
    else:
        context.state = _apply_completed_step_state(
            context.state,
            result=result,
            fingerprint=fingerprint,
            updated_at=entry.occurred_at,
            last_event_id=entry.entry_id,
        )
    context.state_port.save(context.state)


def record_transform_commit(
    context: WorkflowExecutionRecorder,
    commit: WorkflowTransformDestructiveCommit,
) -> None:
    """Record a destructive transform commit that still needs confirmation."""
    entry = context.ledger.record_step_commit_pending_confirmation(
        step_id=commit.step_id,
        step_kind="transform",
        details=commit.details,
    )
    current_step = _find_step_state(context.state, commit.step_id)
    context.state = _record_step_state(
        context.state,
        WorkflowStepState(
            step_id=commit.step_id,
            step_kind="transform",
            status="running" if current_step is None else current_step.status,
            fingerprint=commit.fingerprint,
            destructive=True,
            commit_pending_confirmation=True,
            mutation_details=commit.details,
        ),
        updated_at=entry.occurred_at,
        last_event_id=entry.entry_id,
    )
    context.state = replace(
        context.state,
        repair_required=True,
        repair_hint=(
            "A destructive workflow transform committed before terminal "
            "confirmation. Resume requires explicit --repair-steps or "
            "--force-steps for the ambiguous step."
        ),
        ambiguous_step_ids=tuple(dict.fromkeys((*context.state.ambiguous_step_ids, commit.step_id))),
    )
    context.state_port.save(context.state)


def record_workflow_finished(
    context: WorkflowExecutionRecorder,
    result: WorkflowRunExecutionResult,
    *,
    completed_at: datetime,
    last_start_offset: int | object | None = _UNSET_CURSOR,
    last_limit: int | object | None = _UNSET_CURSOR,
) -> None:
    """Record the final workflow result and persist terminal state."""
    summary = _build_result_summary(result)
    if result.status == "success":
        _record_workflow_success(
            context,
            completed_at=completed_at,
            summary=summary,
            last_start_offset=last_start_offset,
            last_limit=last_limit,
        )
        return
    _record_workflow_failure(
        context, result=result, completed_at=completed_at, summary=summary
    )


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
