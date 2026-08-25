"""Workflow-owned state mutation helpers for execution recording."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from bioetl.application.services.workflow.workflow_runner_service import (
    WorkflowStepExecutionResult,
)
from bioetl.domain.control_plane import WorkflowExecutionState, WorkflowStepState


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


def _find_step_state(
    state: WorkflowExecutionState,
    step_id: str,
) -> WorkflowStepState | None:
    for step in state.steps:
        if step.step_id == step_id:
            return step
    return None


__all__ = [
    "_apply_completed_step_state",
    "_clear_ambiguous_step",
    "_find_step_state",
    "_record_completed_transform_fingerprint",
    "_record_step_state",
    "_remove_step_ids",
]
