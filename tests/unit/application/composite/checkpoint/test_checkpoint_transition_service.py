"""Tests for application-owned composite checkpoint transition seam."""

from __future__ import annotations

import pytest

from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.application.composite.checkpoint.transition_service import (
    apply_recovery_checkpoint_transition,
    apply_validated_checkpoint_transition,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import InvalidStateError


@pytest.mark.unit
def test_validated_checkpoint_transition_uses_domain_fsm_rules() -> None:
    state = CompositeCheckpointState(
        composite_name="composite_activity",
        run_id="run-1",
        state=CompositePipelineState.NOT_STARTED,
    )

    updated = apply_validated_checkpoint_transition(
        state,
        CompositePipelineState.SEED_RUNNING,
    )

    assert updated.state == CompositePipelineState.SEED_RUNNING


@pytest.mark.unit
def test_validated_checkpoint_transition_rejects_invalid_normal_transition() -> None:
    state = CompositeCheckpointState(
        composite_name="composite_activity",
        run_id="run-1",
        state=CompositePipelineState.COMPLETED,
    )

    with pytest.raises(InvalidStateError):
        apply_validated_checkpoint_transition(
            state,
            CompositePipelineState.FAILED,
        )


@pytest.mark.unit
def test_recovery_checkpoint_transition_requires_explicit_reason() -> None:
    state = CompositeCheckpointState(
        composite_name="composite_activity",
        run_id="run-1",
        state=CompositePipelineState.FAILED,
    )

    with pytest.raises(ValueError, match="non-empty reason"):
        apply_recovery_checkpoint_transition(
            state,
            CompositePipelineState.ENRICHING,
            reason=" ",
        )


@pytest.mark.unit
def test_recovery_checkpoint_transition_bypasses_fsm_only_when_named() -> None:
    state = CompositeCheckpointState(
        composite_name="composite_activity",
        run_id="run-1",
        state=CompositePipelineState.FAILED,
    )

    updated = apply_recovery_checkpoint_transition(
        state,
        CompositePipelineState.ENRICHING,
        reason="resume_from_failed",
    )

    assert updated.state == CompositePipelineState.ENRICHING
