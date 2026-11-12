"""Workflow step dispatch preserves pipeline and transform execution context."""

from __future__ import annotations
from types import SimpleNamespace
from unittest.mock import AsyncMock, sentinel
import pytest
from bioetl.application.services.execution import (
    workflow_runner_step_execution as subject,
)
from bioetl.domain.workflow import WorkflowStepConfig, TransformStepConfig

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize("pipeline", [True, False])
async def test_dispatch_uses_typed_executor_without_losing_context(
    pipeline, monkeypatch
):
    execute_pipeline = AsyncMock(return_value=sentinel.result)
    execute_transform = AsyncMock(return_value=sentinel.result)
    monkeypatch.setattr(subject, "execute_pipeline_step", execute_pipeline)
    monkeypatch.setattr(subject, "execute_transform_step", execute_transform)
    deps = SimpleNamespace(
        pipeline_runner=sentinel.runner,
        cohort_resolver=sentinel.cohort,
        metrics=sentinel.metrics,
        monotonic=sentinel.clock,
        snapshot_reader=sentinel.snapshot,
        transform_service=sentinel.transform,
        artifact_sink=sentinel.artifacts,
    )
    options = SimpleNamespace(
        step_started_callback=sentinel.started, workflow_run_id="workflow-run"
    )
    step = (
        WorkflowStepConfig("step", "test_pipeline")
        if pipeline
        else TransformStepConfig("step", "transform")
    )
    outputs = {"parent": sentinel.output}
    labels = {"workflow": "workflow"}
    result = await subject.dispatch_workflow_step(
        deps=deps,
        workflow_name="workflow",
        step=step,
        step_outputs=outputs,
        workflow_context_labels=labels,
        options=options,
        capture_producer_snapshot=True,
    )
    assert result is sentinel.result
    chosen, other = (
        (execute_pipeline, execute_transform)
        if pipeline
        else (execute_transform, execute_pipeline)
    )
    chosen.assert_awaited_once()
    other.assert_not_awaited()
    assert chosen.call_args.kwargs["step"] is step
    assert chosen.call_args.kwargs["workflow_context_labels"] is labels
    if pipeline:
        assert chosen.call_args.kwargs["capture_producer_snapshot"] is True
        assert chosen.call_args.kwargs["upstream_outputs"] is outputs
        assert chosen.call_args.kwargs["workflow_run_id"] == "workflow-run"
    else:
        assert chosen.call_args.kwargs["step_outputs"] is outputs
        assert chosen.call_args.kwargs["options"] is options
