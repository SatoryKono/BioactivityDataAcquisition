"""Internal policy helpers for adapter health-check flow."""

from __future__ import annotations

from dataclasses import dataclass

from httpx import HTTPStatusError, RequestError

from bioetl.domain.ports.resilience import CircuitBreakerPort
from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.infrastructure.adapters.health_check_contract import (
    HEALTH_CHECK_ERRORS,
)
from bioetl.infrastructure.adapters.health_status_policy import (
    TRANSIENT_DEGRADED_STATUS_CODES,
)


@dataclass(frozen=True, slots=True)
class _HealthCheckProbeOutcome:
    """Internal probe result used to build HealthCheckResult consistently."""

    status: HealthStatus
    last_error: str | None = None
    consecutive_failures: int = 0


def resolve_failure_health_status(
    *,
    error: Exception,
    fallback_status: HealthStatus,
) -> HealthStatus:
    """Resolve final health status for failed probe without masking issues."""
    if fallback_status == HealthStatus.UNHEALTHY:
        return HealthStatus.UNHEALTHY
    if fallback_status == HealthStatus.HEALTHY:
        return HealthStatus.DEGRADED
    if isinstance(error, (TimeoutError, ConnectionError, RequestError)):
        return HealthStatus.DEGRADED
    if isinstance(error, HTTPStatusError):
        status_code = error.response.status_code
        if status_code in TRANSIENT_DEGRADED_STATUS_CODES:
            return HealthStatus.DEGRADED
    return fallback_status


def get_consecutive_health_failures(circuit_breaker: CircuitBreakerPort) -> int:
    """Read circuit-breaker failure count with a conservative fallback."""
    try:
        return int(circuit_breaker.get_failure_count())
    except HEALTH_CHECK_ERRORS:
        return 1


def fallback_health_status(circuit_breaker: CircuitBreakerPort) -> HealthStatus:
    """Get fallback health status from circuit-breaker state."""
    from bioetl.infrastructure.adapters.http.health import (
        assess_health_from_circuit_breaker,
    )

    try:
        return assess_health_from_circuit_breaker(circuit_breaker)
    except HEALTH_CHECK_ERRORS:
        return HealthStatus.UNHEALTHY


def build_error_context(circuit_breaker: CircuitBreakerPort) -> JsonDict:
    """Build error context with circuit-breaker info."""
    try:
        cb_state = circuit_breaker.get_state().value
        cb_failures = circuit_breaker.get_failure_count()
    except HEALTH_CHECK_ERRORS:
        cb_state = None
        cb_failures = 0

    return {
        "circuit_breaker_state": cb_state,
        "circuit_breaker_failures": cb_failures,
    }
