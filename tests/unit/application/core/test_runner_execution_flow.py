"""Focused tests for ordinary runner execution flow orchestration."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from bioetl.application.core import runner_execution_flow
from bioetl.application.observability.observer import LifecyclePhase
from bioetl.domain.types import (
    ComponentHealthResult,
    HealthReport,
    HealthStatus,
)
from bioetl.domain.value_objects.dq_anomaly import (
    DQAnomaly,
    DQAnomalySeverity,
    DQAnomalyType,
)
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult
from bioetl.domain.control_plane.run_ledger import ORDINARY_RUN_LEDGER_STAGE_NAMES
from bioetl.application.core.postrun.compact_orchestrator import CompactionResult
from bioetl.application.core.postrun.service import PostrunResult
from bioetl.application.services.medallion_types import VacuumResult


class _ExecutionHost:
    def __init__(self) -> None:
        self.order: list[str] = []
        self.started: list[str] = []
        self.completed: list[str] = []
        self.offset = 17
        self._config = SimpleNamespace(
            pipeline_name="test_runner_pipeline",
            effective_silver_table="silver.test_runner_pipeline",
            effective_gold_table="gold.test_runner_pipeline",
        )
        self._runtime = SimpleNamespace(limit=11, query="kinase", health_check_mode="strict")
        self._services = SimpleNamespace()
        self._executor = SimpleNamespace(
            execute=self._execute_pipeline,
            get_dq_context=lambda: "dq-context",
        )
        self._checkpoint_manager = SimpleNamespace(
            delete_checkpoint=self._delete_checkpoint,
        )
        self._preflight_service = SimpleNamespace(
            validate_infrastructure=self._validate_infrastructure,
            assert_infrastructure_healthy=self._assert_infrastructure_healthy,
        )
        self._postrun_service = SimpleNamespace(run=self._run_postrun)
        self._lifecycle_service = SimpleNamespace(
            prepare_for_run=self._prepare_for_run,
        )
        self._observer = MagicMock()
        self._observer.emit_phase_started.side_effect = self._emit_phase_started
        self._observer.emit_phase_completed.side_effect = self._emit_phase_completed
        self._observer.emit_health_check_result.side_effect = (
            self._emit_health_check_result
        )
        self._observer.emit_health_check_summary.side_effect = (
            self._emit_health_check_summary
        )
        self._observer.emit_dq_anomaly.side_effect = self._emit_dq_anomaly
        self._observer.emit_vacuum_result.side_effect = self._emit_vacuum_result
        self.execute_calls: list[tuple[int | None, int | None, str | None]] = []
        self.postrun_calls: list[tuple[object, object]] = []
        self.health_components: list[str] = []
        self.health_results: list[dict[str, object]] = []
        self.health_summaries: list[tuple[bool, str]] = []
        self.dq_metrics: list[str] = []
        self.vacuum_layers: list[str] = []

    async def _resolve_execution_offset(self) -> int | None:
        await asyncio.sleep(0)
        self.order.append("resolve_offset")
        return self.offset

    def _record_stage_started(self, stage: str) -> None:
        self.started.append(stage)
        self.order.append(f"start:{stage}")

    def _record_stage_completed(self, stage: str) -> None:
        self.completed.append(stage)
        self.order.append(f"complete:{stage}")

    async def _validate_infrastructure(
        self,
        services: object,
        *,
        raise_on_unhealthy: bool = True,
    ) -> HealthReport:
        await asyncio.sleep(0)
        assert services is self._services
        assert raise_on_unhealthy is False
        self.order.append("validate_infrastructure")
        return HealthReport(
            results=[
                ComponentHealthResult(
                    component="storage",
                    status=HealthStatus.HEALTHY,
                    duration_seconds=0.01,
                ),
                ComponentHealthResult(
                    component="data_source",
                    status=HealthStatus.DEGRADED,
                    duration_seconds=0.02,
                ),
            ]
        )

    def _assert_infrastructure_healthy(self, report: HealthReport) -> None:
        self.order.append(f"assert_infrastructure_healthy:{report.is_healthy}")

    async def _prepare_for_run(self, *, config: object, runtime: object) -> None:
        await asyncio.sleep(0)
        assert config is self._config
        assert runtime is self._runtime
        self.order.append("prepare_medallion_layers")

    async def _execute_pipeline(
        self,
        *,
        limit: int | None,
        query: str | None,
        offset: int | None,
    ) -> None:
        await asyncio.sleep(0)
        self.execute_calls.append((limit, offset, query))
        self.order.append("execute_pipeline")

    async def _run_postrun(
        self, *, executor: object, dq_context: object
    ) -> PostrunResult:
        await asyncio.sleep(0)
        self.postrun_calls.append((executor, dq_context))
        self.order.append("postrun")
        return PostrunResult(
            dq=DQResult(
                error_rate=0.05,
                status=DQEvaluationStatus.WARNING,
                anomalies=(
                    DQAnomaly(
                        metric_name="error_rate",
                        current_value=0.05,
                        baseline_mean=0.01,
                        baseline_stddev=0.002,
                        anomaly_type=DQAnomalyType.THRESHOLD_EXCEEDED,
                        severity=DQAnomalySeverity.HIGH,
                        z_score=20.0,
                        timestamp=datetime.now(UTC),
                        message="Error rate exceeded expected range",
                    ),
                ),
                has_critical=False,
                check_duration_ms=5.0,
            ),
            dq_reports=None,
            vacuum=VacuumResult(
                silver_files_removed=2,
                gold_files_removed=1,
                skipped=False,
            ),
            compaction=CompactionResult(status="success", duplicates_removed=3),
        )

    async def _delete_checkpoint(self) -> None:
        await asyncio.sleep(0)
        self.order.append("checkpoint_finalize")

    def _emit_phase_started(self, phase: LifecyclePhase, **_: object) -> float:
        self.order.append(f"observer:start:{phase.value}")
        return 1.0

    def _emit_phase_completed(
        self,
        phase: LifecyclePhase,
        _start_time: float,
        success: bool = True,
        **_: object,
    ) -> None:
        outcome = "success" if success else "failed"
        self.order.append(f"observer:complete:{phase.value}:{outcome}")

    def _emit_health_check_result(self, component: str, **kwargs: object) -> None:
        self.health_components.append(component)
        self.health_results.append({"component": component, **kwargs})
        self.order.append(f"observer:health:{component}")

    def _emit_health_check_summary(
        self,
        *,
        validated: bool,
        overall_status: str,
        **_: object,
    ) -> None:
        self.health_summaries.append((validated, overall_status))
        self.order.append(f"observer:health_summary:{validated}:{overall_status}")

    def _emit_dq_anomaly(self, metric_name: str, **_: object) -> None:
        self.dq_metrics.append(metric_name)
        self.order.append(f"observer:dq:{metric_name}")

    def _emit_vacuum_result(self, layer: str, **_: object) -> None:
        self.vacuum_layers.append(layer)
        self.order.append(f"observer:vacuum:{layer}")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_managed_pipeline_preserves_canonical_stage_order() -> None:
    host = _ExecutionHost()

    await runner_execution_flow.run_managed_pipeline(cast(Any, host))

    assert host.started == list(ORDINARY_RUN_LEDGER_STAGE_NAMES)
    assert host.completed == list(ORDINARY_RUN_LEDGER_STAGE_NAMES)
    assert host.order == [
        "start:preflight",
        "observer:start:preflight",
        "validate_infrastructure",
        "observer:health:storage",
        "observer:health:data_source",
        "observer:health_summary:True:DEGRADED",
        "assert_infrastructure_healthy:True",
        "complete:preflight",
        "observer:complete:preflight:success",
        "start:prepare_medallion_layers",
        "observer:start:lifecycle_clear",
        "prepare_medallion_layers",
        "complete:prepare_medallion_layers",
        "observer:complete:lifecycle_clear:success",
        "resolve_offset",
        "start:execute_pipeline",
        "observer:start:execution",
        "execute_pipeline",
        "complete:execute_pipeline",
        "observer:complete:execution:success",
        "start:postrun",
        "observer:start:postrun",
        "postrun",
        "observer:dq:error_rate",
        "observer:vacuum:silver",
        "observer:vacuum:gold",
        "complete:postrun",
        "observer:complete:postrun:success",
        "start:checkpoint_finalize",
        "observer:start:cleanup",
        "checkpoint_finalize",
        "complete:checkpoint_finalize",
        "observer:complete:cleanup:success",
    ]
    assert host.health_components == ["storage", "data_source"]
    assert host.health_results == [
        {
            "component": "storage",
            "healthy": True,
            "duration_ms": 10.0,
            "provider": None,
            "latency_ms": None,
            "health_check_mode": "strict",
            "fallback_reason": None,
            "health_status": "HEALTHY",
            "runner_stage": "preflight",
        },
        {
            "component": "data_source",
            "healthy": True,
            "duration_ms": 20.0,
            "provider": None,
            "latency_ms": None,
            "health_check_mode": "strict",
            "fallback_reason": None,
            "health_status": "DEGRADED",
            "runner_stage": "preflight",
        },
    ]
    assert host.health_summaries == [(True, "DEGRADED")]
    assert host.dq_metrics == ["error_rate"]
    assert host.vacuum_layers == ["silver", "gold"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_execution_cycle_passes_resolved_offset_to_executor() -> None:
    host = _ExecutionHost()

    await runner_execution_flow.run_execution_cycle(cast(Any, host))

    assert host.execute_calls == [(11, 17, "kinase")]
    assert host.postrun_calls == [(host._executor, "dq-context")]
    assert host.started == list(ORDINARY_RUN_LEDGER_STAGE_NAMES[2:])
    assert host.completed == list(ORDINARY_RUN_LEDGER_STAGE_NAMES[2:])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tracked_stage_emits_failed_phase_completion() -> None:
    host = _ExecutionHost()

    async def _boom() -> None:
        await asyncio.sleep(0)
        host.order.append("boom")
        raise RuntimeError("forced")

    with pytest.raises(RuntimeError, match="forced"):
        await runner_execution_flow._run_tracked_stage(
            cast(Any, host),
            ORDINARY_RUN_LEDGER_STAGE_NAMES[2],
            _boom,
        )

    assert host.started == [ORDINARY_RUN_LEDGER_STAGE_NAMES[2]]
    assert host.completed == []
    assert host.order == [
        "start:execute_pipeline",
        "observer:start:execution",
        "boom",
        "observer:complete:execution:failed",
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_execution_cycle_hands_resolved_context_to_named_stage_runner() -> (
    None
):
    host = _ExecutionHost()
    observed_context: object | None = None

    async def _recording_run_execution_cycle_stages(
        observed_host: object,
        context: object,
    ) -> None:
        await asyncio.sleep(0)
        nonlocal observed_context
        assert observed_host is host
        observed_context = context

    original_helper = runner_execution_flow._run_execution_cycle_stages
    runner_execution_flow._run_execution_cycle_stages = (
        _recording_run_execution_cycle_stages
    )
    try:
        await runner_execution_flow.run_execution_cycle(cast(Any, host))
    finally:
        runner_execution_flow._run_execution_cycle_stages = original_helper

    assert observed_context is not None
    assert observed_context.offset == 17
    assert host.order == ["resolve_offset"]
