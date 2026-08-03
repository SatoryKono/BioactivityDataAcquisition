"""State-transition helpers for provider health monitoring."""

from __future__ import annotations

from typing import Protocol

from bioetl.domain.types import HealthStatus

_ADAPTIVE_PARAMS_BY_STATUS: dict[HealthStatus, tuple[float, int]] = {
    HealthStatus.UNHEALTHY: (4.0, 4),
    HealthStatus.DEGRADED: (2.0, 2),
    HealthStatus.HEALTHY: (1.0, 1),
}


class ProviderHealthStateLike(Protocol):
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
    state: ProviderHealthStateLike,
    *,
    now: float,
) -> bool:
    """Return True when the clear window elapsed since last success."""
    if state.last_success is None:
        return False
    elapsed = now - state.last_success
    return elapsed >= state.CLEAR_WINDOW_SECONDS


def record_success_transition(
    state: ProviderHealthStateLike,
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


def record_error_transition(state: ProviderHealthStateLike) -> HealthStatus:
    """Apply error-driven state transition and return resulting status."""
    state.consecutive_errors += 1

    if state.consecutive_errors >= state.UNHEALTHY_THRESHOLD:
        state.status = HealthStatus.UNHEALTHY
    elif state.consecutive_errors >= state.DEGRADED_THRESHOLD:
        state.status = HealthStatus.DEGRADED

    return state.status


def record_health_check_transition(
    state: ProviderHealthStateLike,
    *,
    status: HealthStatus,
    now: float,
) -> HealthStatus:
    """Apply health-check transition and return resulting status."""
    state.last_check = now

    if status == HealthStatus.UNHEALTHY:
        state.status = HealthStatus.UNHEALTHY
        state.consecutive_errors = state.UNHEALTHY_THRESHOLD
        return state.status

    if status == HealthStatus.HEALTHY:
        if state.status == HealthStatus.UNHEALTHY:
            state.status = HealthStatus.DEGRADED
        elif state.status == HealthStatus.DEGRADED:
            state.status = HealthStatus.HEALTHY
        state.consecutive_errors = 0
        state.last_success = now

    return state.status


def get_adaptive_params_for_status(status: HealthStatus) -> tuple[float, int]:
    """Return timeout and batch-size adjustments for a health status."""
    return _ADAPTIVE_PARAMS_BY_STATUS[status]
