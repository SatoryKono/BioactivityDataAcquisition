"""Canonical mapping for circuit breaker state metrics.

This module centralizes the numeric encoding used by `bioetl_circuit_breaker_state`
so emitters, metric definitions, and dashboards stay consistent.
"""

from __future__ import annotations

__all__ = ["CIRCUIT_BREAKER_STATE_DESCRIPTION"]


from bioetl.domain.types import CircuitBreakerState

CIRCUIT_BREAKER_STATE_VALUES: dict[CircuitBreakerState, float] = {
    CircuitBreakerState.CLOSED: 0.0,
    CircuitBreakerState.HALF_OPEN: 1.0,
    CircuitBreakerState.OPEN: 2.0,
}

CIRCUIT_BREAKER_STATE_DESCRIPTION = (
    "Current state of the circuit breaker (0=closed, 1=half-open, 2=open)"
)
