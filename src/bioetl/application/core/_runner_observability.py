"""Private observer emission helpers for runner execution flow."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import HealthStatus


class _RunnerObservabilityHostProtocol(Protocol):
    _config: object
    _runtime: object
    _observer: object

if TYPE_CHECKING:
    from bioetl.application.core.postrun.service import PostrunResult
    from bioetl.domain.types import HealthReport


def emit_preflight_health_results(
    host: _RunnerObservabilityHostProtocol,
    report: HealthReport | None,
    *,
    runner_stage: str,
) -> None:
    """Emit component-level preflight health results through PipelineObserver."""
    if report is None:
        return
    health_check_mode = getattr(host._runtime, "health_check_mode", "strict")
    for result in report.results:
        host._observer.emit_health_check_result(
            component=result.component,
            healthy=result.status != HealthStatus.UNHEALTHY,
            duration_ms=result.duration_seconds * 1000.0,
            provider=result.provider,
            latency_ms=result.latency_ms,
            health_check_mode=health_check_mode,
            fallback_reason=result.probe_fallback_reason,
            health_status=result.status.value,
            runner_stage=runner_stage,
        )


def emit_postrun_observability(
    host: _RunnerObservabilityHostProtocol,
    result: PostrunResult,
    *,
    runner_stage: str,
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
            runner_stage=runner_stage,
        )

    if result.vacuum.skipped:
        return

    host._observer.emit_vacuum_result(
        layer="silver",
        table=host._config.effective_silver_table,
        files_removed=result.vacuum.silver_files_removed,
        runner_stage=runner_stage,
    )

    if not getattr(host._runtime, "skip_gold", False):
        host._observer.emit_vacuum_result(
            layer="gold",
            table=host._config.effective_gold_table,
            files_removed=result.vacuum.gold_files_removed,
            runner_stage=runner_stage,
        )
