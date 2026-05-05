"""Tests for first-class workflow transform execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from bioetl.application.services.workflow_transform_service import (
    WorkflowTransformService,
    should_skip_transform_step,
)
from bioetl.application.workflow.transforms import WorkflowTransformRegistry
from bioetl.domain.workflow import TransformStepConfig, WorkflowTransformSpec


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


def _service(metrics: _RecordingMetrics) -> WorkflowTransformService:
    registry = WorkflowTransformRegistry()
    registry.register(
        "normalize_activity",
        lambda spec, upstream: {
            "fingerprint": spec.fingerprint,
            "upstream": sorted(upstream),
        },
    )
    return WorkflowTransformService(
        registry=registry,
        metrics=metrics,
        monotonic=iter([10.0, 10.25]).__next__,
    )


@pytest.mark.asyncio
async def test_transform_step_executes_registered_transform() -> None:
    metrics = _RecordingMetrics()
    service = _service(metrics)

    result = await service.run_step(
        workflow_name="activity_workflow",
        step=TransformStepConfig(
            step_id="normalize",
            transform_name="normalize_activity",
            depends_on=("extract",),
        ),
        upstream_outputs={"extract": object()},
    )

    assert result.status == "success"
    assert result.skipped is False
    assert isinstance(result.output, dict)
    assert metrics.counters == [
        (
            "bioetl_workflow_step_events_total",
            1,
            {
                "workflow": "activity_workflow",
                "step_kind": "transform",
                "status": "success",
            },
        )
    ]
    assert metrics.histograms[0][0] == "bioetl_workflow_step_duration_seconds"
    assert metrics.histograms[0][1] == pytest.approx(0.25, rel=1e-6)


@pytest.mark.asyncio
async def test_transform_step_skips_matching_completed_fingerprint() -> None:
    metrics = _RecordingMetrics()
    service = _service(metrics)
    step = TransformStepConfig(
        step_id="normalize",
        transform_name="normalize_activity",
        config={"profile": "activity"},
    )
    spec = WorkflowTransformSpec.from_step(step)

    result = await service.run_step(
        workflow_name="activity_workflow",
        step=step,
        completed_fingerprints={"normalize": spec.fingerprint},
    )

    assert result.status == "skipped"
    assert result.skipped is True
    assert should_skip_transform_step(
        spec,
        completed_fingerprints={"normalize": spec.fingerprint},
    )
    assert metrics.counters[0][2]["status"] == "skipped"


@pytest.mark.asyncio
async def test_transform_step_returns_failed_result_for_executor_error() -> None:
    metrics = _RecordingMetrics()
    registry = WorkflowTransformRegistry()

    def _raise(_spec: WorkflowTransformSpec, _upstream: dict[str, Any]) -> object:
        raise RuntimeError("boom")

    registry.register("normalize_activity", _raise)
    service = WorkflowTransformService(
        registry=registry,
        metrics=metrics,
        monotonic=iter([1.0, 1.1]).__next__,
    )

    result = await service.run_step(
        workflow_name="activity_workflow",
        step=TransformStepConfig(
            step_id="normalize",
            transform_name="normalize_activity",
        ),
    )

    assert result.status == "failed"
    assert result.error_type == "RuntimeError"
    assert metrics.counters[0][2]["status"] == "failed"


@pytest.mark.asyncio
async def test_transform_step_returns_failed_result_for_unknown_transform() -> None:
    metrics = _RecordingMetrics()
    service = WorkflowTransformService(
        registry=WorkflowTransformRegistry(),
        metrics=metrics,
        monotonic=iter([5.0, 5.1]).__next__,
    )

    result = await service.run_step(
        workflow_name="activity_workflow",
        step=TransformStepConfig(
            step_id="normalize",
            transform_name="missing_transform",
        ),
    )

    assert result.status == "failed"
    assert result.error_type == "KeyError"
    assert metrics.counters[0][2]["status"] == "failed"
