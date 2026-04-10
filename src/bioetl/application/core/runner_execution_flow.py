"""Execution lifecycle helpers for :mod:`bioetl.application.core.runner`."""

from __future__ import annotations

__all__ = [
    "execute_pipeline",
    "prepare_medallion_layers",
    "run_execution_cycle",
    "run_managed_pipeline",
    "run_postrun_phase",
    "validate_infrastructure",
]

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bioetl.application.observability.observer import LifecyclePhase
from bioetl.domain.control_plane.run_ledger import ORDINARY_RUN_LEDGER_STAGE_NAMES
from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointManagerService,
    )
    from bioetl.application.core.postrun.service import PostrunResult
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.application.core.postrun.service import PostrunService
    from bioetl.application.core.preflight.service import PreflightService
    from bioetl.application.observability.observer import PipelineObserver
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.types import HealthReport
    from bioetl.domain.value_objects import DQAnomaly


_PREFLIGHT_STAGE_NAME = ORDINARY_RUN_LEDGER_STAGE_NAMES[0]
_PREPARE_MEDALLION_LAYERS_STAGE_NAME = ORDINARY_RUN_LEDGER_STAGE_NAMES[1]
_EXECUTE_PIPELINE_STAGE_NAME = ORDINARY_RUN_LEDGER_STAGE_NAMES[2]
_POSTRUN_STAGE_NAME = ORDINARY_RUN_LEDGER_STAGE_NAMES[3]
_CHECKPOINT_FINALIZE_STAGE_NAME = ORDINARY_RUN_LEDGER_STAGE_NAMES[4]
_PHASE_BY_STAGE_NAME = {
    _PREFLIGHT_STAGE_NAME: LifecyclePhase.PREFLIGHT,
    _PREPARE_MEDALLION_LAYERS_STAGE_NAME: LifecyclePhase.LIFECYCLE_CLEAR,
    _EXECUTE_PIPELINE_STAGE_NAME: LifecyclePhase.EXECUTION,
    _POSTRUN_STAGE_NAME: LifecyclePhase.POSTRUN,
    _CHECKPOINT_FINALIZE_STAGE_NAME: LifecyclePhase.CLEANUP,
}


class _PipelineRunnerExecutionHostProtocol(Protocol):
    _config: PipelineConfig
    _runtime: RuntimeConfig
    _services: PipelineService
    _executor: BatchExecutor
    _checkpoint_manager: CheckpointManagerService
    _preflight_service: PreflightService
    _postrun_service: PostrunService
    _lifecycle_service: MedallionLifecycleService
    _observer: PipelineObserver

    async def _resolve_execution_offset(self) -> int | None: ...

    def _record_stage_started(self, stage: str) -> None: ...

    def _record_stage_completed(self, stage: str) -> None: ...


@dataclass(frozen=True, slots=True)
class _TrackedStage:
    """One ordinary runner stage with its tracked async operation."""

    name: str
    operation: Callable[[], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class _ExecutionCycleContext:
    """Resolved ordinary execution-cycle runtime inputs."""

    offset: int | None


def _phase_for_stage_name(stage_name: str) -> LifecyclePhase:
    """Resolve observer phase name for one canonical runner stage."""
    return _PHASE_BY_STAGE_NAME[stage_name]


def _emit_preflight_health_results(
    host: _PipelineRunnerExecutionHostProtocol,
    report: HealthReport | None,
) -> None:
    """Emit component-level preflight health results through PipelineObserver."""
    if report is None:
        return
    for result in report.results:
        host._observer.emit_health_check_result(
            component=result.component,
            healthy=result.status != HealthStatus.UNHEALTHY,
            duration_ms=result.duration_seconds * 1000.0,
            health_status=result.status.value,
            runner_stage=_PREFLIGHT_STAGE_NAME,
        )


def _emit_postrun_observability(
    host: _PipelineRunnerExecutionHostProtocol,
    result: PostrunResult,
) -> None:
    """Emit DQ anomaly and VACUUM events from one postrun result."""
    for anomaly in result.dq.anomalies:
        host._observer.emit_dq_anomaly(
            metric_name=anomaly.metric_name,
            severity=anomaly.severity.value,
            anomaly_type=anomaly.anomaly_type.value,
            current_value=anomaly.current_value,
            baseline_mean=anomaly.baseline_mean,
            baseline_stddev=anomaly.baseline_stddev,
            z_score=anomaly.z_score,
            message=anomaly.message,
            runner_stage=_POSTRUN_STAGE_NAME,
        )

    if result.vacuum.skipped:
        return

    host._observer.emit_vacuum_result(
        layer="silver",
        table=host._config.effective_silver_table,
        files_removed=result.vacuum.silver_files_removed,
        runner_stage=_POSTRUN_STAGE_NAME,
    )

    if not getattr(host._runtime, "skip_gold", False):
        host._observer.emit_vacuum_result(
            layer="gold",
            table=host._config.effective_gold_table,
            files_removed=result.vacuum.gold_files_removed,
            runner_stage=_POSTRUN_STAGE_NAME,
        )


async def _run_tracked_stage(
    host: _PipelineRunnerExecutionHostProtocol,
    stage_name: str,
    operation: Callable[[], Awaitable[None]],
) -> None:
    """Execute one ordinary runner stage with canonical ledger bookkeeping."""
    phase = _phase_for_stage_name(stage_name)
    host._record_stage_started(stage_name)
    start_time = host._observer.emit_phase_started(
        phase,
        runner_stage=stage_name,
    )
    try:
        await operation()
    except Exception as exc:
        host._observer.emit_phase_completed(
            phase,
            start_time,
            success=False,
            runner_stage=stage_name,
            error_type=type(exc).__name__,
        )
        raise
    host._record_stage_completed(stage_name)
    host._observer.emit_phase_completed(
        phase,
        start_time,
        runner_stage=stage_name,
    )


async def _run_tracked_stages(
    host: _PipelineRunnerExecutionHostProtocol,
    stages: tuple[_TrackedStage, ...],
) -> None:
    """Execute tracked stages in the declared canonical order."""
    for stage in stages:
        await _run_tracked_stage(host, stage.name, stage.operation)


def _managed_pipeline_stages(
    host: _PipelineRunnerExecutionHostProtocol,
) -> tuple[_TrackedStage, ...]:
    """Build the canonical managed-run pre-execution stage sequence."""
    return (
        _TrackedStage(
            name=_PREFLIGHT_STAGE_NAME,
            operation=lambda: validate_infrastructure(host),
        ),
        _TrackedStage(
            name=_PREPARE_MEDALLION_LAYERS_STAGE_NAME,
            operation=lambda: prepare_medallion_layers(host),
        ),
    )


def _execution_cycle_stages(
    host: _PipelineRunnerExecutionHostProtocol,
    *,
    offset: int | None,
) -> tuple[_TrackedStage, ...]:
    """Build the canonical extract/postrun/checkpoint stage sequence."""
    return (
        _TrackedStage(
            name=_EXECUTE_PIPELINE_STAGE_NAME,
            operation=lambda: execute_pipeline(host, offset=offset),
        ),
        _TrackedStage(
            name=_POSTRUN_STAGE_NAME,
            operation=lambda: run_postrun_phase(host),
        ),
        _TrackedStage(
            name=_CHECKPOINT_FINALIZE_STAGE_NAME,
            operation=host._checkpoint_manager.delete_checkpoint,
        ),
    )


async def _resolve_execution_cycle_context(
    host: _PipelineRunnerExecutionHostProtocol,
) -> _ExecutionCycleContext:
    """Resolve ordinary execution-cycle inputs before tracked stage execution."""
    return _ExecutionCycleContext(offset=await host._resolve_execution_offset())


async def _run_execution_cycle_stages(
    host: _PipelineRunnerExecutionHostProtocol,
    context: _ExecutionCycleContext,
) -> None:
    """Execute canonical extract/postrun/checkpoint stages from one context."""
    await _run_tracked_stages(
        host, _execution_cycle_stages(host, offset=context.offset)
    )


async def run_managed_pipeline(host: _PipelineRunnerExecutionHostProtocol) -> None:
    """Run the validated pipeline lifecycle within managed contexts."""
    await _run_tracked_stages(host, _managed_pipeline_stages(host))
    await run_execution_cycle(host)


async def run_execution_cycle(host: _PipelineRunnerExecutionHostProtocol) -> None:
    """Execute extraction, postrun, and checkpoint finalization."""
    context = await _resolve_execution_cycle_context(host)
    await _run_execution_cycle_stages(host, context)


async def execute_pipeline(
    host: _PipelineRunnerExecutionHostProtocol,
    *,
    offset: int | None,
) -> None:
    """Execute the pipeline batch executor with resolved runtime inputs."""
    await host._executor.execute(
        limit=host._runtime.limit,
        query=host._runtime.query,
        offset=offset,
    )


async def run_postrun_phase(host: _PipelineRunnerExecutionHostProtocol) -> None:
    """Run the postrun workflow using the executor's resolved DQ context."""
    dq_context = host._executor.get_dq_context()
    result = await host._postrun_service.run(
        executor=host._executor,
        dq_context=dq_context,
    )
    _emit_postrun_observability(host, result)


async def validate_infrastructure(host: _PipelineRunnerExecutionHostProtocol) -> None:
    """Validate infrastructure health before pipeline execution."""
    report = await host._preflight_service.validate_infrastructure(host._services)
    _emit_preflight_health_results(host, report)


async def prepare_medallion_layers(host: _PipelineRunnerExecutionHostProtocol) -> None:
    """Prepare medallion layers according to the runtime policy."""
    await host._lifecycle_service.prepare_for_run(
        config=host._config,
        runtime=host._runtime,
    )
