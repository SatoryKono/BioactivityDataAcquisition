"""Public adapter-local seam for circuit breaker state-transition contracts."""

from __future__ import annotations

from bioetl.infrastructure.adapters._circuit_breaker_contract import (
    CircuitBreakerAttemptDecision,
    CircuitBreakerSnapshot,
    CircuitBreakerTransition,
    CircuitBreakerTransitionEvent,
    evaluate_attempt,
    on_failure_transition,
    on_success_transition,
    retry_after_seconds,
)

__all__ = [
    "CircuitBreakerAttemptDecision",
    "CircuitBreakerSnapshot",
    "CircuitBreakerTransition",
    "CircuitBreakerTransitionEvent",
    "evaluate_attempt",
    "on_failure_transition",
    "on_success_transition",
    "retry_after_seconds",
]
