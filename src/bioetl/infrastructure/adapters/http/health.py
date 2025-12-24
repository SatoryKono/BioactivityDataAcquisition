"""Health check utilities for HTTP adapters."""

from typing import Any

from bioetl.domain.types import HealthStatus


def assess_health_from_circuit_breaker(circuit_breaker: Any) -> HealthStatus:
    """Determine health status from circuit breaker state.

    Args:
        circuit_breaker: CircuitBreaker instance

    Returns:
        HealthStatus based on state and failure count.

    """
    cb_state = circuit_breaker.get_state()
    failure_count = circuit_breaker.get_failure_count()

    if cb_state.value == "CLOSED" and failure_count == 0:
        return HealthStatus.HEALTHY
    elif failure_count <= 2:
        return HealthStatus.DEGRADED
    else:
        return HealthStatus.UNHEALTHY
