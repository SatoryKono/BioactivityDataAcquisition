# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Integration tests for declarative workflow runner orchestration."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass, field

import pytest

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.workflow.workflow_runner_service import (
    WorkflowRunnerService,
)
from bioetl.application.services.workflow.workflow_transform_service import (
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
from tests.helpers.deterministic_ids import deterministic_run_id

pytestmark = pytest.mark.integration


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
    async def _fake_async_result(self, result: RunResult) -> RunResult:
        await asyncio.sleep(0)
        return result

    def _make_result(
        self,
        pipeline_name: str,
        run_id: object | None = None,
        options: object | None = None,
    ) -> RunResult:
        del run_id, options
        return RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name=pipeline_name,
            run_id=deterministic_run_id(f"workflow_runner:{pipeline_name}"),
            run_type="incremental",
            records_bronze=3,
            records_silver=3,
            started_at=FIXED_TEST_TIME,
            completed_at=FIXED_TEST_TIME,
        )

    def run(
        self,
        pipeline_name: str,
        dry_run: bool = False,
        run_id: object | None = None,
        options: object | None = None,
    ) -> Awaitable[RunResult]:
        del dry_run
        return self._fake_async_result(
            self._make_result(pipeline_name, run_id=run_id, options=options)
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
    assert any(
        name == "bioetl_workflow_current_status"
        and value == 0.0
        and labels["workflow"] == "activity_workflow"
        and labels["pipeline_context"] == "chembl_activity"
        and labels["run_type_context"] == "incremental"
        and labels["provider_context"] == "chembl"
        for name, value, labels in metrics.gauges
    )
    transform_payload = result.steps[1].payload
    assert isinstance(transform_payload, WorkflowTransformExecutionResult)
    assert transform_payload.status == "success"
    assert any(name == "bioetl_workflow_runs_total" for name, _, _ in metrics.counters)
    assert any(
        name == "bioetl_workflow_step_duration_seconds"
        and labels["step_kind"] == "pipeline"
        and labels["status"] == "success"
        and labels["pipeline_context"] == "chembl_activity"
        and labels["run_type_context"] == "incremental"
        and labels["provider_context"] == "chembl"
        for name, _value, labels in metrics.histograms
    )
    assert any(
        name == "bioetl_workflow_step_events_total"
        and labels["step_kind"] == "transform"
        and labels["status"] == "success"
        for name, _value, labels in metrics.counters
    )


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


@pytest.mark.asyncio
async def test_workflow_runner_preserves_topological_order_for_dependency_graph() -> (
    None
):
    metrics = _RecordingMetrics()
    pipeline_runner = _PipelineRunner()
    registry = WorkflowTransformRegistry()
    registry.register("normalize_activity", lambda _spec, upstream: sorted(upstream))
    service = WorkflowRunnerService(
        pipeline_runner=pipeline_runner,  # type: ignore[arg-type]
        transform_service=WorkflowTransformService(
            registry=registry,
            metrics=metrics,
            monotonic=iter([2.0, 2.2]).__next__,
        ),
        metrics=metrics,
    )
    config = WorkflowConfig(
        name="activity_workflow",
        steps=(
            TransformStepConfig(
                step_id="normalize",
                transform_name="normalize_activity",
                depends_on=("extract",),
            ),
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
                run_options=WorkflowRunOptionsConfig(limit=3),
            ),
        ),
    )

    result = await service.run_workflow(config)

    assert result.status == "success"
    assert [step.step_id for step in result.steps] == ["extract", "normalize"]
