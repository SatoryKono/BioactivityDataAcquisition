"""Incomplete replay evidence cannot unlock a blocked legacy checkpoint."""

from dataclasses import replace

import pytest

from bioetl.application.composite.checkpoint._checkpoint_replay_projection import (
    merge_replay_projection_state,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.control_plane.run_ledger import RunLedgerReplayProjection

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "state_changes, projection_changes",
    [
        ({}, {"projector_coverage_complete": False}),
        ({}, {"merge_completed": False}),
        ({"seed_completed": False}, {}),
        ({"seed_result": None}, {}),
        ({}, {"merge_result": None}),
    ],
)
def test_replay_keeps_checkpoint_blocked_until_all_completion_proofs_exist(
    state_changes, projection_changes
):
    state = CompositeCheckpointState(
        composite_name="composite",
        run_id="run",
        legacy_cv_resume_blocked=True,
        seed_completed=True,
        seed_result={"pipeline_name": "seed"},
    )
    projection = RunLedgerReplayProjection(
        projector_coverage_complete=True,
        merge_completed=True,
        merge_result={"records_merged": 1},
    )
    result = merge_replay_projection_state(
        state=replace(state, **state_changes),
        replay_projection=replace(projection, **projection_changes),
    )
    assert result.legacy_cv_resume_blocked is True
    assert result.legacy_cv_completion_pending is False
    assert state.legacy_cv_resume_blocked is True
