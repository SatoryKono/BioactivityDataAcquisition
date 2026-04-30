"""Tests for declarative workflow runner service."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

import pytest

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.workflow_runner_service import WorkflowRunnerService
from bioetl.application.services.workflow_transform_service import (
    WorkflowTransformService,
)
from bioetl.application.workflow.transforms import WorkflowTransformRegistry
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
)
from tests.helpers.clock import FIXED_TEST_TIME


@dataclass
class _RecordingMetrics:
    counters: list[tuple[str, int, dict[str, str]]] = field(default_factory=list)
    histograms: list[tuple[str, float, dict[str, str]]] = field(default_factory=list)

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str] | None = None,
    ) -> None:
        self.counters.append((name, value, labels or {}))

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        self.histograms.append((name, value, labels or {}))

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        del name, value, labels

    def close(self) -> None:
        return None


class _PipelineRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    async def run(
        self,
        pipeline_name: str,
        dry_run: bool = False,
        run_id: object | None = None,
        options: object | None = None,
    ) -> RunResult:
        del dry_run, run_id
        self.calls.append((pipeline_name, options))
        return RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name=pipeline_name,
            run_id=str(uuid4()),
            run_type="incremental",
            started_at=FIXED_TEST_TIME,
            completed_at=FIXED_TEST_TIME,
        )


class _FailingPipelineRunner:
    async def run(
        self,
        pipeline_name: str,
        dry_run: bool = False,
        run_id: object | None = None,
        options: object | None = None,
    ) -> RunResult:
        del pipeline_name, dry_run, run_id, options
        raise RuntimeError("pipeline boom")


@pytest.mark.asyncio
async def test_workflow_runner_executes_pipeline_then_transform() -> None:
    metrics = _RecordingMetrics()
    pipeline_runner = _PipelineRunner()
    registry = WorkflowTransformRegistry()
    registry.register("normalize_activity", lambda _spec, upstream: sorted(upstream))
    transform_service = WorkflowTransformService(
        registry=registry,
        metrics=metrics,
        monotonic=iter([1.0, 1.2]).__next__,
    )
    service = WorkflowRunnerService(
        pipeline_runner=pipeline_runner,  # type: ignore[arg-type]
        transform_service=transform_service,
        metrics=metrics,
    )
    config = WorkflowConfig(
        name="activity_workflow",
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
                run_options=WorkflowRunOptionsConfig(limit=25),
            ),
            TransformStepConfig(
                step_id="normalize",
                transform_name="normalize_activity",
                depends_on=("extract",),
            ),
        ),
    )

    result = await service.run_workflow(config)

    assert result.status == "success"
    assert [step.step_id for step in result.steps] == ["extract", "normalize"]
    assert pipeline_runner.calls[0][0] == "chembl_activity"
    assert metrics.counters[-1] == (
        "bioetl_workflow_runs_total",
        1,
        {"workflow": "activity_workflow", "status": "success"},
    )


@pytest.mark.asyncio
async def test_workflow_runner_returns_failed_step_result_for_pipeline_error() -> None:
    metrics = _RecordingMetrics()
    transform_service = WorkflowTransformService(
        registry=WorkflowTransformRegistry(),
        metrics=metrics,
        monotonic=iter([1.0, 1.2]).__next__,
    )
    service = WorkflowRunnerService(
        pipeline_runner=_FailingPipelineRunner(),  # type: ignore[arg-type]
        transform_service=transform_service,
        metrics=metrics,
    )
    config = WorkflowConfig(
        name="activity_workflow",
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
                run_options=WorkflowRunOptionsConfig(limit=25),
            ),
        ),
    )

    result = await service.run_workflow(config)

    assert result.status == "failed"
    assert result.steps[0].status == "failed"
    assert result.steps[0].error_type == "RuntimeError"
    assert metrics.counters[-1] == (
        "bioetl_workflow_runs_total",
        1,
        {"workflow": "activity_workflow", "status": "failed"},
    )
