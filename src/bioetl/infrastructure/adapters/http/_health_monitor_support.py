"""Internal transition and observability helpers for provider health monitor."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.domain.ports import HealthCheckResult, LoggerPort, MetricsPort


class _ProviderHealthStateLike(Protocol):
    """Minimal mutable state contract used by health-monitor helpers."""

    provider: str
    status: HealthStatus
    consecutive_errors: int
    last_success: float | None
    last_check: float | None
    DEGRADED_THRESHOLD: int
    UNHEALTHY_THRESHOLD: int
    CLEAR_WINDOW_SECONDS: float


def check_clear_window(
    state: _ProviderHealthStateLike,
    *,
    now: float,
) -> bool:
    """Return True when the clear window elapsed since last success."""
    if state.last_success is None:
        return False
    elapsed = now - state.last_success
    return elapsed >= state.CLEAR_WINDOW_SECONDS


def record_success_transition(
    state: _ProviderHealthStateLike,
    *,
    now: float,
) -> HealthStatus:
    """Apply success-driven state transition and return resulting status."""
    state.consecutive_errors = 0
    should_recover_to_healthy = (
        state.status == HealthStatus.DEGRADED and check_clear_window(state, now=now)
    )
    state.last_success = now

    if state.status == HealthStatus.UNHEALTHY:
        state.status = HealthStatus.DEGRADED
    elif should_recover_to_healthy:
        state.status = HealthStatus.HEALTHY

    return state.status


def record_error_transition(state: _ProviderHealthStateLike) -> HealthStatus:
    """Apply error-driven state transition and return resulting status."""
    state.consecutive_errors += 1

    if state.consecutive_errors >= state.UNHEALTHY_THRESHOLD:
        state.status = HealthStatus.UNHEALTHY
    elif state.consecutive_errors >= state.DEGRADED_THRESHOLD:
        state.status = HealthStatus.DEGRADED

    return state.status


def record_health_check_transition(
    state: _ProviderHealthStateLike,
    *,
    status: HealthStatus,
    now: float,
) -> HealthStatus:
    """Apply health-check transition and return resulting status."""
    state.last_check = now

    if status == HealthStatus.UNHEALTHY:
        state.status = HealthStatus.UNHEALTHY
        state.consecutive_errors = state.UNHEALTHY_THRESHOLD
    elif status == HealthStatus.HEALTHY:
        if state.status == HealthStatus.UNHEALTHY:
            state.status = HealthStatus.DEGRADED
        elif state.status == HealthStatus.DEGRADED:
            state.status = HealthStatus.HEALTHY
        state.consecutive_errors = 0
        state.last_success = now

    return state.status


def get_adaptive_params_for_status(status: HealthStatus) -> tuple[float, int]:
    """Return timeout and batch-size adjustments for a health status."""
    if status == HealthStatus.UNHEALTHY:
        return (4.0, 4)
    if status == HealthStatus.DEGRADED:
        return (2.0, 2)
    return (1.0, 1)


def emit_provider_health_metric(
    *,
    metrics: MetricsPort,
    state: _ProviderHealthStateLike,
) -> None:
    """Emit provider health gauge for one provider state."""
    metrics.set_gauge(
        "provider_health_status",
        state.status.to_metric_value(),
        labels={"provider": state.provider},
    )


def emit_health_check_observability(
    *,
    metrics: MetricsPort,
    result: HealthCheckResult,
) -> None:
    """Emit health-check latency, gauge, and success/failure counters."""
    metrics.observe_histogram(
        "health_check_latency_ms",
        result.latency_ms,
        labels={"provider": result.provider},
    )
    metrics.set_gauge(
        "provider_health_status",
        float(result.status.to_metric_value()),
        labels={"provider": result.provider},
    )
    if result.status == HealthStatus.HEALTHY:
        metrics.increment_counter(
            "health_check_success_total",
            1,
            labels={"provider": result.provider},
        )
    else:
        metrics.increment_counter(
            "health_check_failures_total",
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
