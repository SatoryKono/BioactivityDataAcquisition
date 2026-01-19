"""Health check utilities for HTTP adapters.

Provides functions to assess adapter health based on circuit breaker state.
Used by HTTP adapters to implement the health_check() method required by
the HealthCheckPort protocol.

See Also:
    - CircuitBreakerPort: Protocol defining circuit breaker interface
    - ADR-007: Circuit Breaker Implementation decision
"""

from __future__ import annotations

from typing import Any

from bioetl.domain.types import HealthStatus


def assess_health_from_circuit_breaker(circuit_breaker: Any) -> HealthStatus:
    """Determine adapter health status from circuit breaker state.

    Maps circuit breaker state and failure count to a HealthStatus value
    for use in adapter health checks. The mapping follows these rules:

    - HEALTHY: Circuit is CLOSED with zero failures (normal operation)
    - DEGRADED: Circuit has 1-2 failures (experiencing intermittent issues)
    - UNHEALTHY: Circuit has 3+ failures or is OPEN/HALF_OPEN

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
        - UNHEALTHY: Adapter is not operational or has critical failures

    Example:
        >>> from bioetl.infrastructure.adapters.http import CircuitBreaker
        >>> cb = CircuitBreaker(provider="chembl", failure_threshold=5)
        >>> assess_health_from_circuit_breaker(cb)
        <HealthStatus.HEALTHY: 'healthy'>
        >>> # After some failures:
        >>> cb._failure_count = 2  # Simulated failures
        >>> assess_health_from_circuit_breaker(cb)
        <HealthStatus.DEGRADED: 'degraded'>

    See Also:
        - CircuitBreakerPort: Protocol definition in domain/ports/resilience.py
        - RULES.md §3.1.4: Circuit breaker requirements

    """
    cb_state = circuit_breaker.get_state()
    failure_count = circuit_breaker.get_failure_count()

    if cb_state.value == "CLOSED" and failure_count == 0:
        return HealthStatus.HEALTHY
    elif failure_count <= 2:
        return HealthStatus.DEGRADED
    else:
        return HealthStatus.UNHEALTHY
