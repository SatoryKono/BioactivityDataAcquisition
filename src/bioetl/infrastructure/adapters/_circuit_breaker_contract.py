"""Backward-compatible re-export for `bioetl.infrastructure.adapters.circuit_breaker_contract`."""

from __future__ import annotations

from bioetl.infrastructure.adapters import circuit_breaker_contract as _public

CircuitBreakerAttemptDecision = _public.CircuitBreakerAttemptDecision
CircuitBreakerSnapshot = _public.CircuitBreakerSnapshot
CircuitBreakerTransition = _public.CircuitBreakerTransition
CircuitBreakerTransitionEvent = _public.CircuitBreakerTransitionEvent
evaluate_attempt = _public.evaluate_attempt
on_failure_transition = _public.on_failure_transition
on_success_transition = _public.on_success_transition
retry_after_seconds = _public.retry_after_seconds

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
