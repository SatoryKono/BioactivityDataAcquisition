"""Tests for first-class workflow transform execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from bioetl.application.services.workflow_transform_service import (
    WorkflowTransformService,
    should_skip_transform_step,
)
from bioetl.application.workflow.transforms import (
    WorkflowTransformDestructiveCommit,
    WorkflowTransformRegistry,
)
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


@pytest.mark.asyncio
async def test_transform_step_emits_destructive_commit_callback() -> None:
    metrics = _RecordingMetrics()
    registry = WorkflowTransformRegistry()

    def _destructive(
        spec: WorkflowTransformSpec,
        _upstream: dict[str, Any],
        runtime_context: object,
    ) -> object:
        assert hasattr(runtime_context, "record_destructive_commit")
        runtime_context.record_destructive_commit(
            step_id=spec.step_id,
            transform_name=spec.transform_name,
            fingerprint=spec.fingerprint,
            details={"orphan_rows_deleted": 3},
        )
        return {"fingerprint": spec.fingerprint, "mutated": True}

    registry.register("reconcile_foreign_keys", _destructive)
    service = WorkflowTransformService(
        registry=registry,
        metrics=metrics,
        monotonic=iter([2.0, 2.5]).__next__,
    )
    commits: list[WorkflowTransformDestructiveCommit] = []

    result = await service.run_step(
        workflow_name="activity_workflow",
        step=TransformStepConfig(
            step_id="repair_orphans",
            transform_name="reconcile_foreign_keys",
        ),
        destructive_commit_callback=commits.append,
    )

    assert result.status == "success"
    assert len(commits) == 1
    assert commits[0].step_id == "repair_orphans"
    assert commits[0].details["orphan_rows_deleted"] == 3


@pytest.mark.asyncio
async def test_transform_step_passes_dry_run_into_runtime_context() -> None:
    metrics = _RecordingMetrics()
    registry = WorkflowTransformRegistry()

    def _preview(
        spec: WorkflowTransformSpec,
        _upstream: dict[str, Any],
        runtime_context: object,
    ) -> object:
        return {
            "fingerprint": spec.fingerprint,
            "dry_run": getattr(runtime_context, "dry_run", None),
        }

    registry.register("reconcile_foreign_keys", _preview)
    service = WorkflowTransformService(
        registry=registry,
        metrics=metrics,
        monotonic=iter([3.0, 3.2]).__next__,
    )

    result = await service.run_step(
        workflow_name="activity_workflow",
        step=TransformStepConfig(
            step_id="repair_orphans",
            transform_name="reconcile_foreign_keys",
        ),
        dry_run=True,
    )

    assert result.status == "success"
    assert result.output == {
        "fingerprint": result.fingerprint,
        "dry_run": True,
    }


@pytest.mark.asyncio
async def test_transform_step_passes_artifact_context_and_skip_avoids_sink() -> None:
    metrics = _RecordingMetrics()
    registry = WorkflowTransformRegistry()
    seen: dict[str, object] = {}

    def _capture(
        spec: WorkflowTransformSpec,
        _upstream: dict[str, Any],
        runtime_context: object,
    ) -> object:
        seen["workflow_run_id"] = getattr(runtime_context, "workflow_run_id", None)
        seen["manifest_id"] = getattr(runtime_context, "manifest_id", None)
        seen["debug_export_enabled"] = getattr(
            runtime_context,
            "debug_export_enabled",
            None,
        )
        seen["debug_export_dir"] = getattr(runtime_context, "debug_export_dir", None)
        seen["artifact_sink"] = getattr(runtime_context, "artifact_sink", None)
        seen["created_at"] = getattr(runtime_context, "created_at", None)
        return {"fingerprint": spec.fingerprint}

    registry.register("reconcile_foreign_keys", _capture)
    service = WorkflowTransformService(registry=registry, metrics=metrics)
    sink = object()
    created_at = object()
    step = TransformStepConfig(
        step_id="repair_orphans",
        transform_name="reconcile_foreign_keys",
    )

    result = await service.run_step(
        workflow_name="activity_workflow",
        step=step,
        workflow_run_id="workflow-run-1",
        manifest_id="manifest-1",
        debug_export_enabled=True,
        debug_export_dir="artifacts/debug_exports",
        artifact_sink=sink,
        created_at=created_at,  # type: ignore[arg-type]
    )
    skipped = await service.run_step(
        workflow_name="activity_workflow",
        step=step,
        completed_fingerprints={"repair_orphans": result.fingerprint},
        artifact_sink=object(),
    )

    assert result.status == "success"
    assert seen == {
        "workflow_run_id": "workflow-run-1",
        "manifest_id": "manifest-1",
        "debug_export_enabled": True,
        "debug_export_dir": "artifacts/debug_exports",
        "artifact_sink": sink,
        "created_at": created_at,
    }
    assert skipped.status == "skipped"
