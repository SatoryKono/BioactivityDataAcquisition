"""Typed workflow steps reach exactly one executor with the same scope."""

from __future__ import annotations

from unittest.mock import AsyncMock, sentinel
import pytest
from bioetl.application.services.execution import (
    workflow_runner_step_execution as subject,
)
from bioetl.domain.workflow import WorkflowStepConfig, WorkflowTransformSpec

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize("pipeline", [True, False])
async def test_typed_step_reaches_only_its_executor_with_the_same_workflow_scope(
    monkeypatch, pipeline
):
    step = (
        WorkflowStepConfig(step_id="step", pipeline_name="chembl_activity")
        if pipeline
        else WorkflowTransformSpec(step_id="step", transform_name="reconcile")
    )
    pipeline_executor = AsyncMock(return_value=sentinel.pipeline_result)
    transform_executor = AsyncMock(return_value=sentinel.transform_result)
    monkeypatch.setattr(subject, "execute_pipeline_step", pipeline_executor)
    monkeypatch.setattr(subject, "execute_transform_step", transform_executor)
    dependencies = subject.WorkflowStepDispatchDependencies(
        pipeline_runner=sentinel.runner,
        cohort_resolver=None,
        transform_service=sentinel.transform,
        artifact_sink=None,
        metrics=sentinel.metrics,
        monotonic=lambda: 0.0,
        snapshot_reader=None,
    )
    options = subject.TransformStepRuntimeOptions(
        completed_transform_fingerprints=None,
        step_started_callback=None,
        transform_commit_callback=None,
        dry_run=False,
        workflow_run_id="workflow-run",
        manifest_id="manifest",
        debug_export_enabled=False,
        debug_export_dir=None,
        created_at_factory=None,
    )
    outputs, labels = {}, {"task": "contract"}
    result = await subject.dispatch_workflow_step(
        deps=dependencies,
        workflow_name="workflow",
        step=step,
        step_outputs=outputs,
        workflow_context_labels=labels,
        options=options,
        capture_producer_snapshot=True,
    )
    selected, other = (
        (pipeline_executor, transform_executor)
        if pipeline
        else (transform_executor, pipeline_executor)
    )
    assert result is (
        sentinel.pipeline_result if pipeline else sentinel.transform_result
    )
    selected.assert_awaited_once()
    other.assert_not_awaited()
    arguments = selected.await_args.kwargs
    assert arguments["step"] is step
    assert arguments["workflow_name"] == "workflow"
    assert arguments["workflow_context_labels"] is labels
    if pipeline:
        assert arguments["capture_producer_snapshot"] is True
        assert arguments["workflow_run_id"] == "workflow-run"
    else:
        assert arguments["options"] is options
        assert arguments["step_outputs"] is outputs
