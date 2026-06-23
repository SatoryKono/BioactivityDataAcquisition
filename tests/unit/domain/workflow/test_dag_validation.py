"""Unit tests for workflow DAG validation and immutable workflow models."""

from __future__ import annotations

import pytest

from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowRunOptionsConfig,
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


@pytest.mark.unit
def test_single_pipeline_workflow_exposes_concrete_handoff_context() -> None:
    config = WorkflowConfig(
        name="chembl_assay",
        defaults=WorkflowRunOptionsConfig(run_type="backfill"),
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_assay",
            ),
            TransformStepConfig(
                step_id="normalize",
                transform_name="normalize_activity_snapshot",
                depends_on=("extract",),
            ),
        ),
    )

    assert config.pipeline_names == ("chembl_assay",)
    assert config.single_pipeline_name == "chembl_assay"
    assert config.pipeline_context == "chembl_assay"
    assert config.run_type_context == "backfill"
    assert config.provider_context == "chembl"
    assert config.workflow_context_labels == {
        "pipeline_context": "chembl_assay",
        "run_type_context": "backfill",
        "provider_context": "chembl",
    }


@pytest.mark.unit
def test_workflow_run_options_merge_required_persistence_profile() -> None:
    base = WorkflowRunOptionsConfig(
        limit=100,
        required_persistence_profile="replay_ready",
    )
    override = WorkflowRunOptionsConfig(
        required_persistence_profile="degraded_observable",
    )

    merged = base.merged_with(override)

    assert merged.limit == 100
    assert merged.required_persistence_profile == "replay_ready"
    assert merged.to_mapping()["required_persistence_profile"] == ("replay_ready")


@pytest.mark.unit
def test_multi_pipeline_workflow_fail_closes_handoff_context() -> None:
    config = WorkflowConfig(
        name="publication_provider_pack",
        steps=(
            WorkflowStepConfig(
                step_id="crossref",
                pipeline_name="crossref_publication",
            ),
            WorkflowStepConfig(
                step_id="openalex",
                pipeline_name="openalex_publication",
            ),
        ),
    )

    assert config.pipeline_names == ("crossref_publication", "openalex_publication")
    assert config.single_pipeline_name is None
    assert config.pipeline_context == "unknown"
    assert config.run_type_context == "All"
    assert config.provider_context == "unknown"
