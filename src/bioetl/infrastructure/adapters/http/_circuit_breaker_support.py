"""Private support helpers for HTTP circuit breaker state transitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from bioetl.domain.exceptions import BioETLError
from bioetl.domain.types import CircuitBreakerState
from bioetl.infrastructure.adapters.circuit_breaker_contract import (
    CircuitBreakerSnapshot,
    CircuitBreakerTransitionEvent,
    evaluate_attempt,
    on_failure_transition,
    on_success_transition,
    retry_after_seconds,
)
from bioetl.infrastructure.observability.circuit_breaker_mapping import (
    CIRCUIT_BREAKER_STATE_VALUES,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort

METRIC_CIRCUIT_BREAKER_SUCCESS = "bioetl_circuit_breaker_success_total"
METRIC_CIRCUIT_BREAKER_FAILURE = "bioetl_circuit_breaker_failure_total"

CALL_OPERATION_ERRORS: tuple[type[Exception], ...] = (
    BioETLError,
    httpx.HTTPError,
    OSError,
    RuntimeError,
)


def emit_state_metric(
    metrics: MetricsPort | None,
    *,
    provider: str,
    state: CircuitBreakerState,
    metric_name: str,
) -> None:
    """Emit current state as a gauge metric when metrics are enabled."""
    if metrics is None:
        return

    metrics.set_gauge(
        metric_name,
        CIRCUIT_BREAKER_STATE_VALUES[state],
        {"adapter": provider},
    )


def emit_counter_metric(
    metrics: MetricsPort | None,
    *,
    provider: str,
    metric_name: str,
) -> None:
    """Increment a circuit-breaker counter metric when metrics are enabled."""
    if metrics is None:
        return

    metrics.increment_counter(
        metric_name,
        1,
        {"adapter": provider},
    )


def decide_attempt_state(
    *,
    state: CircuitBreakerState,
    last_failure_time: float,
    recovery_timeout: int,
    now: float,
    metrics: MetricsPort | None,
    provider: str,
    state_metric_name: str,
) -> tuple[bool, CircuitBreakerState]:
    """Return whether request execution is allowed and the next circuit state."""
    decision = evaluate_attempt(
        CircuitBreakerSnapshot(
            state=state,
            failure_count=0,
            recovery_timeout=float(recovery_timeout),
            last_failure_time=last_failure_time,
        ),
        now=now,
    )
    if decision.event == CircuitBreakerTransitionEvent.HALF_OPENED:
        emit_state_metric(
            metrics,
            provider=provider,
            state=decision.next_state,
            metric_name=state_metric_name,
        )
    return decision.allow_request, decision.next_state


def record_success(
    *,
    state: CircuitBreakerState,
    metrics: MetricsPort | None,
    provider: str,
    state_metric_name: str,
) -> CircuitBreakerState:
    """Record a successful protected call and return the next state."""
    emit_counter_metric(
        metrics,
        provider=provider,
        metric_name=METRIC_CIRCUIT_BREAKER_SUCCESS,
    )
    transition = on_success_transition(
        CircuitBreakerSnapshot(
            state=state,
            failure_count=0,
            recovery_timeout=0.0,
        )
    )
    if transition.event == CircuitBreakerTransitionEvent.CLOSED:
        emit_state_metric(
            metrics,
            provider=provider,
            state=transition.next_state,
            metric_name=state_metric_name,
        )
    return transition.next_state


def record_failure(
    *,
    state: CircuitBreakerState,
    failure_count: int,
    failure_threshold: int,
    metrics: MetricsPort | None,
    provider: str,
    state_metric_name: str,
    trip_metric_name: str,
) -> tuple[CircuitBreakerState, int, int]:
    """Record a failed protected call and return next state, count, and trips."""
    emit_counter_metric(
        metrics,
        provider=provider,
        metric_name=METRIC_CIRCUIT_BREAKER_FAILURE,
    )
    transition = on_failure_transition(
        CircuitBreakerSnapshot(
            state=state,
            failure_count=failure_count,
            recovery_timeout=0.0,
        ),
        failure_threshold=failure_threshold,
    )
    if transition.event == CircuitBreakerTransitionEvent.OPENED:
        emit_state_metric(
            metrics,
            provider=provider,
            state=transition.next_state,
            metric_name=state_metric_name,
        )
        emit_counter_metric(
            metrics,
            provider=provider,
            metric_name=trip_metric_name,
        )
    return transition.next_state, transition.failure_count, transition.trips_delta


def time_until_retry(
    *,
    state: CircuitBreakerState,
    last_failure_time: float,
    recovery_timeout: int,
    now: float,
) -> float:
    """Calculate time remaining until the next OPEN-state retry is allowed."""
    return retry_after_seconds(
        CircuitBreakerSnapshot(
            state=state,
            failure_count=0,
            recovery_timeout=float(recovery_timeout),
            last_failure_time=last_failure_time,
        ),
        now=now,
    )


def is_circuit_breaker_error(exc: Exception) -> bool:
    """Return whether an exception should contribute to breaker decisions."""
    if isinstance(
        exc,
        httpx.ConnectError | httpx.ConnectTimeout | httpx.ReadTimeout | httpx.ReadError,
    ):
        return True

    if isinstance(exc, httpx.HTTPStatusError):
        status_code: int = exc.response.status_code
        return status_code >= 500 or status_code == 429

    return False
