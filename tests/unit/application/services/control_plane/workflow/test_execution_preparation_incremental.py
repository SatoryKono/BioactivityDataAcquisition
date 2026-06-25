"""Focused behavioral tests for incremental workflow execution preparation."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.workflow.execution_preparation_incremental import (
    _apply_incremental_offset,
)
from bioetl.domain.control_plane import WorkflowExecutionState
from bioetl.domain.types import RunID
from bioetl.domain.workflow import TransformStepConfig, WorkflowConfig, WorkflowStepConfig
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
