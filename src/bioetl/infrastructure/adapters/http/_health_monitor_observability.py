"""Observability helpers for provider health monitoring."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http._health_monitor_transitions import (
    ProviderHealthStateLike,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import HealthCheckResult, LoggerPort, MetricsPort

_OUTCOME_COUNTERS: dict[HealthStatus, str] = {
    HealthStatus.HEALTHY: "bioetl_health_check_success_total",
    HealthStatus.DEGRADED: "bioetl_health_check_degraded_total",
    HealthStatus.UNHEALTHY: "bioetl_health_check_failures_total",
}


def emit_provider_health_metric(
    *,
    metrics: MetricsPort,
    state: ProviderHealthStateLike,
) -> None:
    """Emit provider health gauge for one provider state."""
    metrics.set_gauge(
        "bioetl_provider_health_status",
        state.status.to_metric_value(),
        labels={"provider": state.provider},
    )


def emit_health_check_observability(
    *,
    metrics: MetricsPort,
    result: HealthCheckResult,
) -> None:
    """Emit health-check latency, gauge, and outcome counters."""
    metrics.observe_histogram(
        "bioetl_health_check_latency_seconds",
        result.latency_ms / 1000.0,
        labels={"provider": result.provider},
    )
    metrics.set_gauge(
        "bioetl_provider_health_status",
        float(result.status.to_metric_value()),
        labels={"provider": result.provider},
    )
    metrics.increment_counter(
        _OUTCOME_COUNTERS[result.status],
        1,
        labels={"provider": result.provider},
    )


def emit_unhealthy_alert(
    *,
    logger: LoggerPort | None,
    result: HealthCheckResult,
    new_status: HealthStatus,
) -> None:
    """Emit P2 alert when a provider becomes unhealthy."""
    if new_status != HealthStatus.UNHEALTHY or logger is None:
        return
    logger.error(
        "provider_unhealthy_alert",
        provider=result.provider,
        alert_priority="P2",
        status=new_status.value,
        consecutive_failures=result.consecutive_failures,
        last_error=result.last_error,
        endpoint=result.endpoint,
        latency_ms=result.latency_ms,
    )
