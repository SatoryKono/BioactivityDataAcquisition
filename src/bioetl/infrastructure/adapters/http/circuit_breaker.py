"""Circuit breaker for fault tolerance.

Implements RULES.md Section 3.1.4 circuit breaker pattern.

State machine:
    CLOSED -> OPEN (after failure_threshold consecutive errors)
    OPEN -> HALF_OPEN (after recovery_timeout)
    HALF_OPEN -> CLOSED (on success) or OPEN (on failure)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ParamSpec, TypeVar

import httpx

from bioetl.domain.exceptions import CircuitBreakerOpenError
from bioetl.domain.types import CircuitBreakerState

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class CircuitBreaker:
    """Circuit breaker implementation for HTTP clients.

    Protects against cascading failures by temporarily blocking requests
    to failing services.

    Args:
        provider: Provider name for metrics/logging
        failure_threshold: Consecutive failures before opening (default: 5)
        recovery_timeout: Seconds to wait in OPEN before testing (default: 300)

    Example:
        >>> cb = CircuitBreaker(provider="chembl", failure_threshold=5)
        >>> result = await cb.call(fetch_data, url="https://api.example.com")

    Metrics emitted:
        - circuit_breaker_state{provider}: 0=Closed, 1=Half-Open, 2=Open
        - circuit_breaker_trips_total{provider}: Counter of OPEN transitions

    """

    provider: str
    failure_threshold: int = 5
    recovery_timeout: int = 300  # 5 minutes

    _state: CircuitBreakerState = field(init=False, default=CircuitBreakerState.CLOSED)
    _failure_count: int = field(init=False, default=0)
    _last_failure_time: float = field(init=False, default=0.0)
    _trips_total: int = field(init=False, default=0)
    _lock: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)

    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self._state

    def get_failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    def get_trips_total(self) -> int:
        """Get total number of times circuit has opened."""
        return self._trips_total

    def _should_attempt(self) -> bool:
        """Check if request should be attempted based on state."""
        if self._state == CircuitBreakerState.CLOSED:
            return True

        if self._state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = CircuitBreakerState.HALF_OPEN
                return True
            return False

        # HALF_OPEN: allow single probe request
        return True

    def _on_success(self) -> None:
        """Handle successful request."""
        self._failure_count = 0
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._state = CircuitBreakerState.CLOSED

    def _on_failure(self) -> None:
        """Handle failed request."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitBreakerState.HALF_OPEN:
            # Failed probe request, go back to OPEN
            self._state = CircuitBreakerState.OPEN
            self._trips_total += 1
        elif (
            self._state == CircuitBreakerState.CLOSED
            and self._failure_count >= self.failure_threshold
        ):
            # Threshold reached, open circuit
            self._state = CircuitBreakerState.OPEN
            self._trips_total += 1

    def _time_until_retry(self) -> float:
        """Calculate time until next retry is allowed."""
        if self._state != CircuitBreakerState.OPEN:
            return 0.0
        elapsed = time.monotonic() - self._last_failure_time
        return max(0.0, self.recovery_timeout - elapsed)

    async def call(
        self,
        func: Callable[P, Awaitable[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        """Execute function with circuit breaker protection.

        Args:
            func: Async function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Re-raises exceptions from func

        """
        async with self._lock:
            if not self._should_attempt():
                retry_after = self._time_until_retry()
                raise CircuitBreakerOpenError(self.provider, retry_after)

        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                self._on_success()
            return result
        except Exception:
            async with self._lock:
                self._on_failure()
            raise

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0

    def force_open(self) -> None:
        """Manually force circuit breaker to OPEN state."""
        self._state = CircuitBreakerState.OPEN
        self._last_failure_time = time.monotonic()
        self._trips_total += 1


def is_circuit_breaker_error(exc: Exception) -> bool:
    """Check if exception should trigger circuit breaker.

    Only connection/timeout errors should trigger circuit breaker,
    not business logic errors (4xx responses except 429).
    """
    if isinstance(exc, httpx.ConnectError | httpx.ConnectTimeout | httpx.ReadTimeout):
        return True

    if isinstance(exc, httpx.HTTPStatusError):
        # Only 5xx and 429 (rate limit) trigger circuit breaker
        status_code: int = exc.response.status_code
        return status_code >= 500 or status_code == 429

    return False
