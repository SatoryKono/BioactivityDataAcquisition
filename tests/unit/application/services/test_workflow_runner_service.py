"""Tests for declarative workflow runner service."""

from __future__ import annotations

import asyncio
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
    WorkflowTransformSpec,
)
from tests.helpers.clock import FIXED_TEST_TIME


@dataclass
class _RecordingMetrics:
    counters: list[tuple[str, int, dict[str, str]]] = field(default_factory=list)
    gauges: list[tuple[str, float, dict[str, str]]] = field(default_factory=list)
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
        self.gauges.append((name, value, labels or {}))

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
        await asyncio.sleep(0)
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
        await asyncio.sleep(0)
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
                run_options=WorkflowRunOptionsConfig(
                    limit=25,
                    required_persistence_profile="degraded_observable",
                ),
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
    assert pipeline_runner.calls[0][1].required_persistence_profile == (
        "degraded_observable"
    )
    assert metrics.gauges[-1] == (
        "bioetl_workflow_current_status",
        0.0,
        {
            "workflow": "activity_workflow",
            "pipeline_context": "chembl_activity",
            "run_type_context": "incremental",
            "provider_context": "chembl",
        },
    )
    assert metrics.counters[-1] == (
        "bioetl_workflow_runs_total",
        1,
        {
            "workflow": "activity_workflow",
            "status": "success",
            "pipeline_context": "chembl_activity",
            "run_type_context": "incremental",
            "provider_context": "chembl",
        },
    )
    assert any(
        name == "bioetl_workflow_step_duration_seconds"
        and labels
        == {
            "workflow": "activity_workflow",
            "step_kind": "pipeline",
            "status": "success",
            "pipeline_context": "chembl_activity",
            "run_type_context": "incremental",
            "provider_context": "chembl",
        }
        for name, _value, labels in metrics.histograms
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
    assert metrics.gauges[-1] == (
        "bioetl_workflow_current_status",
        2.0,
        {
            "workflow": "activity_workflow",
            "pipeline_context": "chembl_activity",
            "run_type_context": "incremental",
            "provider_context": "chembl",
        },
    )
    assert result.steps[0].status == "failed"
    assert result.steps[0].error_type == "RuntimeError"
    assert metrics.counters[-1] == (
        "bioetl_workflow_runs_total",
        1,
        {
            "workflow": "activity_workflow",
            "status": "failed",
            "pipeline_context": "chembl_activity",
            "run_type_context": "incremental",
            "provider_context": "chembl",
        },
    )


@pytest.mark.asyncio
async def test_workflow_runner_marks_downstream_steps_skipped_after_failure() -> None:
    metrics = _RecordingMetrics()
    service = WorkflowRunnerService(
        pipeline_runner=_FailingPipelineRunner(),  # type: ignore[arg-type]
        transform_service=WorkflowTransformService(
            registry=WorkflowTransformRegistry(),
            metrics=metrics,
            monotonic=iter([1.0, 1.2]).__next__,
        ),
        metrics=metrics,
        monotonic=iter([5.0, 5.3]).__next__,
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

    assert result.status == "failed"
    assert [step.status for step in result.steps] == ["failed", "skipped"]
    assert result.steps[1].error_type == "UpstreamStepFailed"
    assert "extract" in (result.steps[1].error_message or "")
    assert (
        "bioetl_workflow_step_events_total",
        1,
        {
            "workflow": "activity_workflow",
            "step_kind": "transform",
            "status": "skipped",
            "pipeline_context": "chembl_activity",
            "run_type_context": "incremental",
            "provider_context": "chembl",
        },
    ) in metrics.counters


@pytest.mark.asyncio
async def test_workflow_runner_skips_completed_steps_on_resume() -> None:
    metrics = _RecordingMetrics()
    pipeline_runner = _PipelineRunner()
    service = WorkflowRunnerService(
        pipeline_runner=pipeline_runner,  # type: ignore[arg-type]
        transform_service=WorkflowTransformService(
            registry=WorkflowTransformRegistry(),
            metrics=metrics,
        ),
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
            WorkflowStepConfig(
                step_id="enrich",
                pipeline_name="chembl_assay",
                depends_on=("extract",),
            ),
        ),
    )

    result = await service.run_workflow(
        config,
        completed_step_ids=frozenset({"extract"}),
    )

    assert result.status == "success"
    assert [step.status for step in result.steps] == ["skipped", "success"]
    assert result.steps[0].error_type == "AlreadyCompletedOnResume"
    assert len(pipeline_runner.calls) == 1
    assert pipeline_runner.calls[0][0] == "chembl_assay"


@pytest.mark.asyncio
async def test_workflow_runner_callbacks_follow_start_then_complete_order() -> None:
    metrics = _RecordingMetrics()
    pipeline_runner = _PipelineRunner()
    registry = WorkflowTransformRegistry()
    registry.register("normalize_activity", lambda _spec, upstream: sorted(upstream))
    service = WorkflowRunnerService(
        pipeline_runner=pipeline_runner,  # type: ignore[arg-type]
        transform_service=WorkflowTransformService(
            registry=registry,
            metrics=metrics,
        ),
        metrics=metrics,
    )
    config = WorkflowConfig(
        name="activity_workflow",
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
            ),
            TransformStepConfig(
                step_id="normalize",
                transform_name="normalize_activity",
                depends_on=("extract",),
            ),
        ),
    )
    events: list[tuple[str, str, str | None, str | None]] = []

    result = await service.run_workflow(
        config,
        step_started_callback=lambda step, fingerprint=None: events.append(
            ("started", step.step_id, getattr(step, "transform_name", None), fingerprint)
        ),
        step_completed_callback=lambda result: events.append(
            ("completed", result.step_id, result.status, None)
        ),
    )

    assert result.status == "success"
    assert events[0] == ("started", "extract", None, None)
    assert events[1] == ("completed", "extract", "success", None)
    assert events[2][0:3] == ("started", "normalize", "normalize_activity")
    assert isinstance(events[2][3], str)
    assert events[3] == ("completed", "normalize", "success", None)


@pytest.mark.asyncio
async def test_workflow_runner_callbacks_record_failed_then_skipped_transition() -> None:
    metrics = _RecordingMetrics()
    service = WorkflowRunnerService(
        pipeline_runner=_FailingPipelineRunner(),  # type: ignore[arg-type]
        transform_service=WorkflowTransformService(
            registry=WorkflowTransformRegistry(),
            metrics=metrics,
        ),
        metrics=metrics,
    )
    config = WorkflowConfig(
        name="activity_workflow",
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
            ),
            TransformStepConfig(
                step_id="normalize",
                transform_name="normalize_activity",
                depends_on=("extract",),
            ),
        ),
    )
    events: list[tuple[str, str, str | None]] = []

    result = await service.run_workflow(
        config,
        step_started_callback=lambda step, fingerprint=None: events.append(
            ("started", step.step_id, fingerprint)
        ),
        step_completed_callback=lambda result: events.append(
            ("completed", result.step_id, result.status)
        ),
    )

    assert result.status == "failed"
    assert events == [
        ("started", "extract", None),
        ("completed", "extract", "failed"),
        ("completed", "normalize", "skipped"),
    ]


@pytest.mark.asyncio
async def test_workflow_runner_transform_fingerprint_skip_still_emits_callbacks() -> None:
    metrics = _RecordingMetrics()
    pipeline_runner = _PipelineRunner()
    registry = WorkflowTransformRegistry()
    registry.register("normalize_activity", lambda _spec, _upstream: "should-not-run")
    service = WorkflowRunnerService(
        pipeline_runner=pipeline_runner,  # type: ignore[arg-type]
        transform_service=WorkflowTransformService(
            registry=registry,
            metrics=metrics,
        ),
        metrics=metrics,
    )
    config = WorkflowConfig(
        name="activity_workflow",
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
            ),
            TransformStepConfig(
                step_id="normalize",
                transform_name="normalize_activity",
                depends_on=("extract",),
            ),
        ),
    )
    transform_step = config.get_step("normalize")
    assert isinstance(transform_step, TransformStepConfig)
    fingerprint = WorkflowTransformSpec.from_step(transform_step).fingerprint
    events: list[tuple[str, str, str | None]] = []

    result = await service.run_workflow(
        config,
        completed_transform_fingerprints={"normalize": fingerprint},
        step_started_callback=lambda step, fingerprint=None: events.append(
            ("started", step.step_id, fingerprint)
        ),
        step_completed_callback=lambda result: events.append(
            ("completed", result.step_id, result.status)
        ),
    )

    assert result.status == "success"
    assert result.steps[1].status == "skipped"
    assert events[0] == ("started", "extract", None)
    assert events[1] == ("completed", "extract", "success")
    assert events[2][0:2] == ("started", "normalize")
    assert isinstance(events[2][2], str)
    assert events[3] == ("completed", "normalize", "skipped")
