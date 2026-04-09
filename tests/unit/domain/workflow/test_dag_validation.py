"""Unit tests for workflow DAG validation and immutable workflow models."""

from __future__ import annotations

import pytest

from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowDagValidationError,
    WorkflowStepConfig,
    topologically_sorted_step_ids,
)


@pytest.mark.unit
def test_workflow_config_returns_topological_step_ids() -> None:
    config = WorkflowConfig(
        name="example",
        steps=(
            WorkflowStepConfig(step_id="extract", pipeline_name="chembl_activity"),
            TransformStepConfig(
                step_id="normalize",
                transform_name="normalize_activity_snapshot",
                depends_on=("extract",),
            ),
            WorkflowStepConfig(
                step_id="publish",
                pipeline_name="pubchem_activity",
                depends_on=("normalize",),
            ),
        ),
    )

    assert config.topological_step_ids == ("extract", "normalize", "publish")
    assert topologically_sorted_step_ids(config.steps) == (
        "extract",
        "normalize",
        "publish",
    )


@pytest.mark.unit
def test_workflow_config_rejects_duplicate_step_ids() -> None:
    with pytest.raises(WorkflowDagValidationError, match="duplicate step_id"):
        WorkflowConfig(
            name="example",
            steps=(
                WorkflowStepConfig(step_id="extract", pipeline_name="chembl_activity"),
                TransformStepConfig(
                    step_id="extract",
                    transform_name="normalize_activity_snapshot",
                ),
            ),
        )


@pytest.mark.unit
def test_workflow_config_rejects_missing_dependencies() -> None:
    with pytest.raises(WorkflowDagValidationError, match="unknown dependencies"):
        WorkflowConfig(
            name="example",
            steps=(
                WorkflowStepConfig(
                    step_id="extract",
                    pipeline_name="chembl_activity",
                    depends_on=("missing_step",),
                ),
            ),
        )


@pytest.mark.unit
def test_workflow_config_rejects_dependency_cycles() -> None:
    with pytest.raises(WorkflowDagValidationError, match="cycle"):
        WorkflowConfig(
            name="example",
            steps=(
                WorkflowStepConfig(
                    step_id="extract",
                    pipeline_name="chembl_activity",
                    depends_on=("publish",),
                ),
                WorkflowStepConfig(
                    step_id="publish",
                    pipeline_name="pubchem_activity",
                    depends_on=("extract",),
                ),
            ),
        )
