"""Workflow execution ledger/state recording helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from bioetl.application.services.control_plane.workflow.ledger_service import (
    WorkflowLedgerService,
)
from bioetl.application.services.workflow_runner_service import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
    WorkflowTransformDestructiveCommit,
)
from bioetl.domain.control_plane import WorkflowExecutionState, WorkflowStepState
from bioetl.domain.ports import WorkflowExecutionStatePort
from bioetl.domain.workflow import TransformStepConfig, WorkflowStepConfig

__all__ = [
    "WorkflowExecutionRecorder",
    "record_step_completed",
    "record_step_started",
    "record_transform_commit",
    "record_workflow_finished",
    "record_workflow_started",
]


@dataclass(slots=True)
class WorkflowExecutionRecorder:
    """Mutable recording context for one locked workflow execution."""

    ledger: WorkflowLedgerService
    state_port: WorkflowExecutionStatePort
    state: WorkflowExecutionState


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
        details=_fingerprint_details(fingerprint),
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
        ambiguous_step_ids=tuple(
            dict.fromkeys((*context.state.ambiguous_step_ids, commit.step_id))
        ),
    )
    context.state_port.save(context.state)


def record_workflow_finished(
    context: WorkflowExecutionRecorder,
    result: WorkflowRunExecutionResult,
    *,
    completed_at: datetime,
    last_start_offset: int | None = None,
    last_limit: int | None = None,
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
        context,
        result=result,
        completed_at=completed_at,
        summary=summary,
    )


def _record_workflow_success(
    context: WorkflowExecutionRecorder,
    *,
    completed_at: datetime,
    summary: dict[str, object],
    last_start_offset: int | None = None,
    last_limit: int | None = None,
) -> None:
    entry = context.ledger.record_workflow_finished(details=summary)
    context.state = replace(
        context.state,
        status="success",
        updated_at=entry.occurred_at,
        completed_at=completed_at,
        last_event_id=entry.entry_id,
        last_error_type=None,
        last_error_message=None,
        last_start_offset=last_start_offset,
        last_limit=last_limit,
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


def _apply_completed_step_state(
    state: WorkflowExecutionState,
    *,
    result: WorkflowStepExecutionResult,
    fingerprint: str | None,
    updated_at: datetime,
    last_event_id: str,
) -> WorkflowExecutionState:
    state = _record_step_state(
        state,
        WorkflowStepState(
            step_id=result.step_id,
            step_kind=result.step_kind,
            status=result.status,
            fingerprint=fingerprint,
            error_type=result.error_type,
            error_message=result.error_message,
        ),
        updated_at=updated_at,
        last_event_id=last_event_id,
    )
    if result.step_kind == "transform" and result.status == "success":
        state = _record_completed_transform_fingerprint(
            state,
            step_id=result.step_id,
            fingerprint=fingerprint,
        )
    return _clear_ambiguous_step(state, result.step_id)


def _record_step_state(
    state: WorkflowExecutionState,
    step_state: WorkflowStepState,
    *,
    updated_at: datetime,
    last_event_id: str,
) -> WorkflowExecutionState:
    updated_steps = []
    replaced_existing = False
    for current_step in state.steps:
        if current_step.step_id == step_state.step_id:
            updated_steps.append(step_state)
            replaced_existing = True
            continue
        updated_steps.append(current_step)
    if not replaced_existing:
        updated_steps.append(step_state)
    return replace(
        state,
        steps=tuple(updated_steps),
        updated_at=updated_at,
        last_event_id=last_event_id,
        last_error_type=step_state.error_type,
        last_error_message=step_state.error_message,
    )


def _record_completed_transform_fingerprint(
    state: WorkflowExecutionState,
    *,
    step_id: str,
    fingerprint: str | None,
) -> WorkflowExecutionState:
    if fingerprint is None:
        return state
    updated_fingerprints = dict(state.completed_transform_fingerprints)
    updated_fingerprints[step_id] = fingerprint
    return replace(state, completed_transform_fingerprints=updated_fingerprints)


def _clear_ambiguous_step(
    state: WorkflowExecutionState,
    step_id: str,
) -> WorkflowExecutionState:
    ambiguous_step_ids = tuple(
        current_id for current_id in state.ambiguous_step_ids if current_id != step_id
    )
    return replace(
        state,
        repair_required=bool(ambiguous_step_ids),
        repair_hint=None if not ambiguous_step_ids else state.repair_hint,
        ambiguous_step_ids=ambiguous_step_ids,
    )


def _remove_step_ids(
    current_step_ids: tuple[str, ...],
    removed_step_ids: tuple[str, ...],
) -> tuple[str, ...]:
    removed = set(removed_step_ids)
    return tuple(step_id for step_id in current_step_ids if step_id not in removed)


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


def _find_step_state(
    state: WorkflowExecutionState,
    step_id: str,
) -> WorkflowStepState | None:
    for step in state.steps:
        if step.step_id == step_id:
            return step
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
