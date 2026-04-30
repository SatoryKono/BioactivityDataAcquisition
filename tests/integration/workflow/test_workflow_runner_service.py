"""Integration tests for declarative workflow runner orchestration."""

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
    WorkflowTransformExecutionResult,
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

pytestmark = pytest.mark.integration


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
    async def run(
        self,
        pipeline_name: str,
        dry_run: bool = False,
        run_id: object | None = None,
        options: object | None = None,
    ) -> RunResult:
        del dry_run, run_id, options
        return RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name=pipeline_name,
            run_id=str(uuid4()),
            run_type="incremental",
            records_bronze=3,
            records_silver=3,
            started_at=FIXED_TEST_TIME,
            completed_at=FIXED_TEST_TIME,
        )


def _build_config() -> WorkflowConfig:
    return WorkflowConfig(
        name="activity_workflow",
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
                run_options=WorkflowRunOptionsConfig(resume=True, limit=3),
            ),
            TransformStepConfig(
                step_id="normalize",
                transform_name="normalize_activity",
                depends_on=("extract",),
                config={"profile": "activity"},
            ),
        ),
    )


@pytest.mark.asyncio
async def test_workflow_runner_roundtrips_pipeline_transform_and_metrics() -> None:
    metrics = _RecordingMetrics()
    registry = WorkflowTransformRegistry()
    registry.register(
        "normalize_activity",
        lambda spec, upstream: {
            "fingerprint": spec.fingerprint,
            "upstream_steps": sorted(upstream),
        },
    )
    service = WorkflowRunnerService(
        pipeline_runner=_PipelineRunner(),  # type: ignore[arg-type]
        transform_service=WorkflowTransformService(
            registry=registry,
            metrics=metrics,
            monotonic=iter([2.0, 2.5]).__next__,
        ),
        metrics=metrics,
    )

    result = await service.run_workflow(_build_config())

    assert result.is_success
    assert [step.status for step in result.steps] == ["success", "success"]
    transform_payload = result.steps[1].payload
    assert isinstance(transform_payload, WorkflowTransformExecutionResult)
    assert transform_payload.status == "success"
    assert any(name == "bioetl_workflow_runs_total" for name, _, _ in metrics.counters)


@pytest.mark.asyncio
async def test_workflow_runner_skips_completed_transform_by_fingerprint() -> None:
    metrics = _RecordingMetrics()
    config = _build_config()
    transform_step = config.get_step("normalize")
    assert isinstance(transform_step, TransformStepConfig)
    fingerprint = WorkflowTransformSpec.from_step(transform_step).fingerprint
    registry = WorkflowTransformRegistry()
    registry.register("normalize_activity", lambda _spec, _upstream: "should-not-run")
    service = WorkflowRunnerService(
        pipeline_runner=_PipelineRunner(),  # type: ignore[arg-type]
        transform_service=WorkflowTransformService(registry=registry, metrics=metrics),
        metrics=metrics,
    )

    result = await service.run_workflow(
        config,
        completed_transform_fingerprints={"normalize": fingerprint},
    )

    assert result.status == "success"
    assert result.steps[1].status == "skipped"
