"""Focused behavioral tests for incremental workflow execution preparation."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.workflow.execution_preparation_incremental import (
    _apply_incremental_offset,
    _next_incremental_start_offset,
    _offset_from_successful_state,
    _workflow_step_with_start_offset,
)
from bioetl.domain.control_plane import WorkflowExecutionState
from bioetl.domain.types import RunID
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
)
from tests.helpers.clock import FIXED_TEST_TIME


pytestmark = pytest.mark.unit


@dataclass
class _WorkflowStatePortStub:
    latest_state: WorkflowExecutionState | None = None

    def get_latest(self, _workflow_name: str) -> WorkflowExecutionState | None:
        return self.latest_state


def _incremental_workflow() -> WorkflowConfig:
    return WorkflowConfig(
        name="chembl_incremental",
        steps=(
            WorkflowStepConfig(
                step_id="chembl_activity_ingest",
                pipeline_name="chembl_activity",
            ),
            TransformStepConfig(
                step_id="repair_crosswalk",
                transform_name="repair_crosswalk",
                config={"mode": "bounded"},
            ),
        ),
    )


def _workflow_state(
    *,
    status: str = "success",
    last_start_offset: int | None = 25,
    last_limit: int | None = 50,
) -> WorkflowExecutionState:
    return WorkflowExecutionState(
        workflow_run_id=RunID(UUID("00000000-0000-0000-0000-000000000593")),
        manifest_id=f"workflow-manifest-{status}",
        workflow_name="chembl_incremental",
        execution_fingerprint=f"fingerprint-{status}",
        status=status,
        started_at=FIXED_TEST_TIME,
        updated_at=FIXED_TEST_TIME,
        completed_at=FIXED_TEST_TIME,
        selected_step_ids=("chembl_activity_ingest",),
        steps=(),
        completed_transform_fingerprints={},
        last_start_offset=last_start_offset,
        last_limit=last_limit,
    )


@pytest.mark.unit
def test_apply_incremental_offset_returns_original_config_without_successful_state() -> (
    None
):
    config = _incremental_workflow()
    failed_state = WorkflowExecutionState(
        workflow_run_id=RunID(UUID("00000000-0000-0000-0000-000000000591")),
        manifest_id="workflow-manifest-failed",
        workflow_name=config.name,
        execution_fingerprint="fingerprint-failed",
        status="failed",
        started_at=FIXED_TEST_TIME,
        updated_at=FIXED_TEST_TIME,
        completed_at=FIXED_TEST_TIME,
        selected_step_ids=("chembl_activity_ingest",),
        steps=(),
        completed_transform_fingerprints={},
        last_start_offset=25,
        last_limit=50,
    )

    updated = _apply_incremental_offset(
        config=config,
        workflow_state_port=_WorkflowStatePortStub(latest_state=failed_state),
    )

    assert updated is config
    assert updated.defaults.start_offset is None


@pytest.mark.unit
def test_apply_incremental_offset_rewrites_pipeline_steps_but_not_transform_steps() -> (
    None
):
    config = _incremental_workflow()
    prior_state = WorkflowExecutionState(
        workflow_run_id=RunID(UUID("00000000-0000-0000-0000-000000000592")),
        manifest_id="workflow-manifest-success",
        workflow_name=config.name,
        execution_fingerprint="fingerprint-success",
        status="success",
        started_at=FIXED_TEST_TIME,
        updated_at=FIXED_TEST_TIME,
        completed_at=FIXED_TEST_TIME,
        selected_step_ids=("chembl_activity_ingest",),
        steps=(),
        completed_transform_fingerprints={},
        last_start_offset=None,
        last_limit=40,
    )

    updated = _apply_incremental_offset(
        config=config,
        workflow_state_port=_WorkflowStatePortStub(latest_state=prior_state),
    )

    assert updated.defaults.start_offset == 40
    assert updated.steps[0].run_options.start_offset == 40
    assert updated.steps[1] is config.steps[1]
    assert updated.steps[1].step_id == "repair_crosswalk"


@pytest.mark.unit
def test_next_incremental_start_offset_uses_workflow_name_and_prior_window() -> None:
    """Offset lookup is deterministic from the latest successful state window."""

    @dataclass
    class _RecordingWorkflowStatePortStub:
        latest_state: WorkflowExecutionState
        requested_workflow_names: list[str]

        def get_latest(self, workflow_name: str) -> WorkflowExecutionState:
            self.requested_workflow_names.append(workflow_name)
            return self.latest_state

    port = _RecordingWorkflowStatePortStub(
        latest_state=_workflow_state(last_start_offset=10, last_limit=15),
        requested_workflow_names=[],
    )

    assert (
        _next_incremental_start_offset(
            workflow_state_port=port,
            workflow_name="chembl_incremental",
        )
        == 25
    )
    assert port.requested_workflow_names == ["chembl_incremental"]


@pytest.mark.unit
def test_offset_from_successful_state_requires_success_and_limit() -> None:
    """Only complete successful windows can advance the next start offset."""
    assert _offset_from_successful_state(None) is None
    assert _offset_from_successful_state(_workflow_state(status="failed")) is None
    assert (
        _offset_from_successful_state(_workflow_state(last_start_offset=25, last_limit=None))
        is None
    )
    assert (
        _offset_from_successful_state(_workflow_state(last_start_offset=25, last_limit=50))
        == 75
    )


@pytest.mark.unit
def test_workflow_step_with_start_offset_preserves_other_run_options() -> None:
    """Incremental replay rewrites only offset, preserving bounded run options."""
    original = WorkflowStepConfig(
        step_id="chembl_activity_ingest",
        pipeline_name="chembl_activity",
        run_options=WorkflowRunOptionsConfig(
            limit=25,
            required_persistence_profile="degraded_observable",
        ),
    )

    updated = _workflow_step_with_start_offset(original, 125)

    assert updated is not original
    assert updated.run_options.start_offset == 125
    assert updated.run_options.limit == 25
    assert updated.run_options.required_persistence_profile == "degraded_observable"
