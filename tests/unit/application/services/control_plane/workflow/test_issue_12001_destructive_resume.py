"""Acceptance for destructive resume selectors (#12001)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from bioetl.application.services.workflow.control_plane import execution_recording
from bioetl.application.services.workflow.control_plane._execution_resume_support import (
    resolve_completed_transform_fingerprints,
    resolve_skipped_step_ids,
    validate_resume_state,
)
from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowStepExecutionResult,
)
from bioetl.domain.control_plane import WorkflowStepState

from .test_execution_recording import _make_context

pytestmark = pytest.mark.unit

_STARTED = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
_FINGERPRINT = "fingerprint-1"


def _ambiguous_steps() -> tuple[WorkflowStepState, WorkflowStepState]:
    return (
        WorkflowStepState(
            step_id="step_a",
            step_kind="transform",
            status="running",
            fingerprint="fp-a",
            destructive=True,
            commit_pending_confirmation=True,
        ),
        WorkflowStepState(
            step_id="step_b",
            step_kind="transform",
            status="running",
            fingerprint="fp-b",
            destructive=True,
            commit_pending_confirmation=True,
        ),
    )


def test_selector_b_does_not_clear_or_replay_a() -> None:
    context, _saved = _make_context()
    context.state = replace(
        context.state,
        status="incomplete",
        execution_fingerprint=_FINGERPRINT,
        selected_step_ids=("step_a", "step_b"),
        steps=_ambiguous_steps(),
        completed_transform_fingerprints={"step_a": "fp-a", "step_b": "fp-b"},
        repair_required=True,
        repair_hint="confirm destructive commits",
        ambiguous_step_ids=("step_a", "step_b"),
    )

    execution_recording.record_workflow_started(
        context,
        resumed=True,
        repair_steps=("step_b",),
        force_steps=(),
    )

    assert context.state.ambiguous_step_ids == ("step_a", "step_b")
    assert context.state.repair_required is True
    assert resolve_skipped_step_ids(
        state=context.state,
        force_steps=(),
        repair_steps=("step_b",),
    ) == frozenset({"step_a"})
    assert resolve_completed_transform_fingerprints(
        state=context.state,
        force_steps=(),
        repair_steps=("step_b",),
    ) == {"step_a": "fp-a"}

    execution_recording.record_step_completed(
        context,
        WorkflowStepExecutionResult(
            step_id="step_b",
            step_kind="transform",
            status="failed",
            error_type="RuntimeError",
            error_message="repair failed",
        ),
    )

    step_b = next(step for step in context.state.steps if step.step_id == "step_b")
    assert context.state.ambiguous_step_ids == ("step_a", "step_b")
    assert step_b.commit_pending_confirmation is True
    assert context.state.repair_required is True
    with pytest.raises(RuntimeError, match="confirm destructive commits"):
        validate_resume_state(
            latest_state=context.state,
            workflow_name=context.state.workflow_name,
            current_fingerprint=_FINGERPRINT,
            force_steps=(),
            repair_steps=(),
        )

    execution_recording.record_step_completed(
        context,
        WorkflowStepExecutionResult(
            step_id="step_b",
            step_kind="transform",
            status="success",
            payload={"fingerprint": "fp-b-confirmed"},
        ),
    )

    confirmed = next(step for step in context.state.steps if step.step_id == "step_b")
    assert context.state.ambiguous_step_ids == ("step_a",)
    assert context.state.repair_required is True
    assert confirmed.commit_pending_confirmation is False
    assert confirmed.status == "success"
