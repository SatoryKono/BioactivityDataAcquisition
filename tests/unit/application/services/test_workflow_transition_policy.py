"""Focused tests for pure workflow step transition policy."""

from __future__ import annotations

from bioetl.application.services.workflow_transition_policy import (
    apply_step_result_transition,
    resolve_step_transition_policy,
    step_kind_for_config,
)
from bioetl.domain.workflow import TransformStepConfig, WorkflowStepConfig


def test_resolve_step_transition_policy_runs_when_no_failure_or_resume_anchor() -> None:
    step = WorkflowStepConfig(step_id="extract", pipeline_name="chembl_activity")

    policy = resolve_step_transition_policy(
        step,
        failed_step_id=None,
        completed_step_ids=None,
    )

    assert policy.disposition == "run"
    assert policy.stores_output is True
    assert policy.failed_step_id is None
    assert policy.should_run is True


def test_resolve_step_transition_policy_skips_after_upstream_failure() -> None:
    step = TransformStepConfig(
        step_id="normalize",
        transform_name="normalize_activity",
        depends_on=("extract",),
    )

    policy = resolve_step_transition_policy(
        step,
        failed_step_id="extract",
        completed_step_ids=frozenset({"normalize"}),
    )

    assert policy.disposition == "skip_failed"
    assert policy.stores_output is False
    assert policy.failed_step_id == "extract"
    assert policy.should_run is False


def test_resolve_step_transition_policy_skips_completed_step_on_resume() -> None:
    step = WorkflowStepConfig(step_id="extract", pipeline_name="chembl_activity")

    policy = resolve_step_transition_policy(
        step,
        failed_step_id=None,
        completed_step_ids=frozenset({"extract"}),
    )

    assert policy.disposition == "skip_completed"
    assert policy.stores_output is False
    assert policy.failed_step_id is None


def test_apply_step_result_transition_marks_failed_step_once() -> None:
    step = WorkflowStepConfig(step_id="extract", pipeline_name="chembl_activity")

    status, failed_step_id = apply_step_result_transition(
        step=step,
        result_status="failed",
        workflow_status="success",
        failed_step_id=None,
    )

    assert status == "failed"
    assert failed_step_id == "extract"


def test_apply_step_result_transition_preserves_existing_failed_anchor() -> None:
    step = WorkflowStepConfig(step_id="normalize", pipeline_name="chembl_activity")

    status, failed_step_id = apply_step_result_transition(
        step=step,
        result_status="success",
        workflow_status="failed",
        failed_step_id="extract",
    )

    assert status == "failed"
    assert failed_step_id == "extract"


def test_step_kind_for_config_distinguishes_pipeline_and_transform() -> None:
    pipeline_step = WorkflowStepConfig(
        step_id="extract",
        pipeline_name="chembl_activity",
    )
    transform_step = TransformStepConfig(
        step_id="normalize",
        transform_name="normalize_activity",
        depends_on=("extract",),
    )

    assert step_kind_for_config(pipeline_step) == "pipeline"
    assert step_kind_for_config(transform_step) == "transform"
