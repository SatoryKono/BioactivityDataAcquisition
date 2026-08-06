"""Circuit breaker for fault tolerance.

Implements RULES.md Section 3.1.4 circuit breaker pattern.
"""

from __future__ import annotations

__all__ = [
    "METRIC_CIRCUIT_BREAKER_OPEN_TOTAL",
    "METRIC_CIRCUIT_BREAKER_STATE",
    "METRIC_CIRCUIT_BREAKER_TRIPS",
    "CircuitBreakerGuard",
    "P",
    "T",
    "is_circuit_breaker_error",
]

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ParamSpec, TypeVar

from bioetl.domain.exceptions import CircuitBreakerOpenError
from bioetl.domain.types import CircuitBreakerState
from bioetl.infrastructure.adapters.http._circuit_breaker_support import (
    CALL_OPERATION_ERRORS,
    decide_attempt_state,
    emit_counter_metric,
    emit_state_metric,
    is_circuit_breaker_error,
    record_failure,
    record_success,
    time_until_retry,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from bioetl.domain.ports import MetricsPort

P = ParamSpec("P")
T = TypeVar("T")

METRIC_CIRCUIT_BREAKER_STATE = "bioetl_circuit_breaker_state"
METRIC_CIRCUIT_BREAKER_OPEN_TOTAL = "bioetl_circuit_breaker_open_total"
METRIC_CIRCUIT_BREAKER_TRIPS = "bioetl_circuit_breaker_trips_total"


def _now() -> float:
    """Return the current monotonic time for circuit breaker state decisions."""
    return time.monotonic()


@dataclass
class CircuitBreakerGuard:
    """Circuit breaker implementation for HTTP clients.

    Protects against cascading failures by temporarily blocking requests
    to failing services.

    Args:
        provider: Provider name for metrics/logging
        failure_threshold: Consecutive failures before opening (default: 5)
        recovery_timeout: Seconds to wait in OPEN before testing (default: 300)
        metrics: Optional MetricsPort for emitting circuit breaker metrics

    Example:
        >>> cb = CircuitBreakerGuard(provider="chembl", failure_threshold=5)
        >>> result = await cb.call(fetch_data, url="https://api.example.com")

    Metrics emitted:
        - circuit_breaker_state{adapter}: 0=Closed, 1=Half-Open, 2=Open
        - circuit_breaker_trips_total{adapter}: Counter of OPEN transitions
        - circuit_breaker_success_total{adapter}: Counter of successful calls
        - circuit_breaker_failure_total{adapter}: Counter of failed calls

    """

    provider: str
    failure_threshold: int = 5
    recovery_timeout: int = 300  # 5 minutes
    metrics: MetricsPort | None = None

    _state: CircuitBreakerState = field(init=False, default=CircuitBreakerState.CLOSED)
    _failure_count: int = field(init=False, default=0)
    _last_failure_time: float = field(init=False, default=0.0)
    _trips_total: int = field(init=False, default=0)
    _lock: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)

    def __post_init__(self) -> None:
        """Emit initial state metric after initialization."""
        emit_state_metric(
            self.metrics,
            provider=self.provider,
            state=self._state,
            metric_name=METRIC_CIRCUIT_BREAKER_STATE,
        )

    def get_state(self) -> CircuitBreakerState:
        """Return current circuit breaker state."""
        return self._state

    def get_failure_count(self) -> int:
        """Return current consecutive failure count."""
        return self._failure_count

    def get_recovery_timeout(self) -> float:
        """Seconds to wait in OPEN before a HALF_OPEN probe is allowed."""
        return float(self.recovery_timeout)

    def get_last_failure_time(self) -> float | None:
        """Monotonic timestamp of the last recorded failure, if any."""
        if self._last_failure_time <= 0.0:
            return None
        return float(self._last_failure_time)

    def snapshot(self) -> object:
        """Return a public typed snapshot of circuit-breaker state.

        Prefer this over reading private fields such as ``_last_failure_time``.
        Returns a ``CircuitBreakerSnapshot`` instance.
        """
        from bioetl.infrastructure.adapters.circuit_breaker_contract import (
            CircuitBreakerSnapshot,
        )

        return CircuitBreakerSnapshot(
            state=self.get_state(),
            failure_count=self.get_failure_count(),
            recovery_timeout=self.get_recovery_timeout(),
            last_failure_time=self.get_last_failure_time(),
        )

    def get_trips_total(self) -> int:
        """Return cumulative OPEN transitions since initialization."""
        return self._trips_total

    async def call(
        self,
        func: Callable[P, Awaitable[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        """Execute function with circuit breaker protection.

        Uses a single lock acquisition for the state check to avoid
        the overhead of 3 separate lock round-trips per call. The
        function itself executes outside the lock, and state updates
        use a second acquisition only on completion.

        Args:
            func: Async function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Re-raises operational exceptions from func after failure accounting

        """
        async with self._lock:
            now = _now()
            should_attempt, self._state = decide_attempt_state(
                state=self._state,
                last_failure_time=self._last_failure_time,
                recovery_timeout=self.recovery_timeout,
                now=now,
                metrics=self.metrics,
                provider=self.provider,
                state_metric_name=METRIC_CIRCUIT_BREAKER_STATE,
            )
            if not should_attempt:
                emit_counter_metric(
                    self.metrics,
                    provider=self.provider,
                    metric_name=METRIC_CIRCUIT_BREAKER_OPEN_TOTAL,
                )
                raise CircuitBreakerOpenError(
                    self.provider,
                    time_until_retry(
                        state=self._state,
                        last_failure_time=self._last_failure_time,
                        recovery_timeout=self.recovery_timeout,
                        now=now,
                    ),
                )

        try:
            result = await func(*args, **kwargs)
        except CALL_OPERATION_ERRORS:
            async with self._lock:
                self._last_failure_time = _now()
                self._state, self._failure_count, trips_delta = record_failure(
                    state=self._state,
                    failure_count=self._failure_count,
                    failure_threshold=self.failure_threshold,
                    metrics=self.metrics,
                    provider=self.provider,
                    state_metric_name=METRIC_CIRCUIT_BREAKER_STATE,
                    trip_metric_name=METRIC_CIRCUIT_BREAKER_TRIPS,
                )
                self._trips_total += trips_delta
            raise
        else:
            async with self._lock:
                self._failure_count = 0
                self._state = record_success(
                    state=self._state,
                    metrics=self.metrics,
                    provider=self.provider,
                    state_metric_name=METRIC_CIRCUIT_BREAKER_STATE,
                )
            return result

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        emit_state_metric(
            self.metrics,
            provider=self.provider,
            state=self._state,
            metric_name=METRIC_CIRCUIT_BREAKER_STATE,
        )

    def force_open(self) -> None:
        """Manually force circuit breaker to OPEN state."""
        self._state = CircuitBreakerState.OPEN
        self._last_failure_time = _now()
        self._trips_total += 1
        emit_state_metric(
            self.metrics,
            provider=self.provider,
            state=self._state,
            metric_name=METRIC_CIRCUIT_BREAKER_STATE,
        )
        emit_counter_metric(
            self.metrics,
            provider=self.provider,
            metric_name=METRIC_CIRCUIT_BREAKER_TRIPS,
        )
