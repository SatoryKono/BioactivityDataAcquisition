"""Shared internal contract for circuit breaker state and transition semantics."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from bioetl.domain.types import CircuitBreakerState


class CircuitBreakerTransitionEvent(StrEnum):
    """Canonical transition events emitted by circuit breaker state logic."""

    NONE = "none"
    OPENED = "opened"
    HALF_OPENED = "half_opened"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class CircuitBreakerSnapshot:
    """Typed snapshot of circuit breaker state used by internal helpers."""

    state: CircuitBreakerState
    failure_count: int
    recovery_timeout: float
    last_failure_time: float | None = None


@dataclass(frozen=True, slots=True)
class CircuitBreakerAttemptDecision:
    """Decision returned before a protected operation begins."""

    allow_request: bool
    next_state: CircuitBreakerState
    event: CircuitBreakerTransitionEvent
    retry_after: float = 0.0


@dataclass(frozen=True, slots=True)
class CircuitBreakerTransition:
    """Transition result returned after success/failure handling."""

    next_state: CircuitBreakerState
    failure_count: int
    trips_delta: int
    event: CircuitBreakerTransitionEvent


def retry_after_seconds(snapshot: CircuitBreakerSnapshot, *, now: float) -> float:
    """Return remaining retry delay for an OPEN breaker snapshot."""
    if snapshot.state != CircuitBreakerState.OPEN:
        return 0.0
    if snapshot.last_failure_time is None:
        return max(0.0, snapshot.recovery_timeout)
    return max(0.0, snapshot.recovery_timeout - (now - snapshot.last_failure_time))


def evaluate_attempt(
    snapshot: CircuitBreakerSnapshot,
    *,
    now: float,
) -> CircuitBreakerAttemptDecision:
    """Return whether a request may proceed and which state should apply."""
    if snapshot.state == CircuitBreakerState.CLOSED:
        return CircuitBreakerAttemptDecision(
            allow_request=True,
            next_state=CircuitBreakerState.CLOSED,
            event=CircuitBreakerTransitionEvent.NONE,
        )

    if snapshot.state == CircuitBreakerState.HALF_OPEN:
        return CircuitBreakerAttemptDecision(
            allow_request=True,
            next_state=CircuitBreakerState.HALF_OPEN,
            event=CircuitBreakerTransitionEvent.NONE,
        )

    retry_after = retry_after_seconds(snapshot, now=now)
    if (
        math.isclose(retry_after, 0.0, abs_tol=1e-12)
        and snapshot.last_failure_time is not None
    ):
        return CircuitBreakerAttemptDecision(
            allow_request=True,
            next_state=CircuitBreakerState.HALF_OPEN,
            event=CircuitBreakerTransitionEvent.HALF_OPENED,
        )

    return CircuitBreakerAttemptDecision(
        allow_request=False,
        next_state=CircuitBreakerState.OPEN,
        event=CircuitBreakerTransitionEvent.NONE,
        retry_after=retry_after,
    )


def on_success_transition(snapshot: CircuitBreakerSnapshot) -> CircuitBreakerTransition:
    """Return the next state after a successful protected operation."""
    if snapshot.state == CircuitBreakerState.HALF_OPEN:
        return CircuitBreakerTransition(
            next_state=CircuitBreakerState.CLOSED,
            failure_count=0,
            trips_delta=0,
            event=CircuitBreakerTransitionEvent.CLOSED,
        )

    return CircuitBreakerTransition(
        next_state=snapshot.state,
        failure_count=0,
        trips_delta=0,
        event=CircuitBreakerTransitionEvent.NONE,
    )


def on_failure_transition(
    snapshot: CircuitBreakerSnapshot,
    *,
    failure_threshold: int,
) -> CircuitBreakerTransition:
    """Return the next state after a failed protected operation."""
    next_failure_count = snapshot.failure_count + 1
    should_open = snapshot.state == CircuitBreakerState.HALF_OPEN or (
        snapshot.state == CircuitBreakerState.CLOSED
        and next_failure_count >= failure_threshold
    )
    if not should_open:
        return CircuitBreakerTransition(
            next_state=snapshot.state,
            failure_count=next_failure_count,
            trips_delta=0,
            event=CircuitBreakerTransitionEvent.NONE,
        )

    return CircuitBreakerTransition(
        next_state=CircuitBreakerState.OPEN,
        failure_count=next_failure_count,
        trips_delta=1,
        event=CircuitBreakerTransitionEvent.OPENED,
    )
