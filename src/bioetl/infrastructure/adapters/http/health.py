"""Health check utilities for HTTP adapters.

Provides functions to assess adapter health based on circuit breaker state.
Used by HTTP adapters to implement the health_check() method required by
the HealthCheckPort protocol.

See Also:
    - CircuitBreakerPort: Protocol defining circuit breaker interface
    - ADR-007: Circuit Breaker Implementation decision
"""

from __future__ import annotations

__all__ = ["assess_health_from_circuit_breaker"]


from bioetl.domain.ports import CircuitBreakerPort
from bioetl.domain.types import HealthStatus


def assess_health_from_circuit_breaker(
    circuit_breaker: CircuitBreakerPort,
) -> HealthStatus:
    """Determine adapter health status from circuit breaker state.

    Maps circuit breaker state to a HealthStatus value for use in adapter
    health checks. The mapping respects the circuit breaker's own configured
    failure_threshold rather than using hardcoded counts:

    - HEALTHY: Circuit is CLOSED with zero failures (normal operation)
    - DEGRADED: Circuit is CLOSED with some failures, or HALF_OPEN (recovering)
    - UNHEALTHY: Circuit is OPEN (failure_threshold reached, blocking requests)

    This function expects a circuit breaker implementing CircuitBreakerPort
    with get_state() and get_failure_count() methods.

    Args:
        circuit_breaker: Instance implementing CircuitBreakerPort protocol.
            Must have get_state() returning CircuitBreakerState and
            get_failure_count() returning int.

    Returns:
        HealthStatus enum value:
        - HEALTHY: Adapter is fully operational
        - DEGRADED: Adapter is functional but experiencing issues
        - UNHEALTHY: Adapter is not operational (circuit breaker tripped)

    Example:
        >>> from bioetl.infrastructure.adapters.http import CircuitBreakerGuard
        >>> cb = CircuitBreakerGuard(provider="chembl", failure_threshold=5)
        >>> assess_health_from_circuit_breaker(cb)
        <HealthStatus.HEALTHY: 'healthy'>
        >>> # After some failures (below threshold):
        >>> cb._failure_count = 3  # Below threshold of 5
        >>> assess_health_from_circuit_breaker(cb)
        <HealthStatus.DEGRADED: 'degraded'>

    See Also:
        - CircuitBreakerPort: Protocol definition in domain/ports/resilience.py
        - RULES.md §3.1.4: Circuit breaker requirements

    """
    cb_state = circuit_breaker.get_state()
    failure_count = circuit_breaker.get_failure_count()

    if cb_state.value == "OPEN":
        return HealthStatus.UNHEALTHY
    if cb_state.value == "HALF_OPEN":
        return HealthStatus.DEGRADED
    # CLOSED state
    if failure_count == 0:
        return HealthStatus.HEALTHY
    return HealthStatus.DEGRADED
