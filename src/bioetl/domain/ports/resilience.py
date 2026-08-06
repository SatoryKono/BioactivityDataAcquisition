"""Resilience ports for rate limiting and circuit breaking.

Implements RULES.md §3.1 - Fault tolerance patterns.
Ports define contracts for SRP-compliant resilience components.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ParamSpec, Protocol, TypeVar, runtime_checkable

from bioetl.domain.types import CircuitBreakerState

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

__all__ = [
    "CircuitBreakerPort",
    "P",
    "RateLimiterPort",
    "T",
]


P = ParamSpec("P")
T = TypeVar("T")


@runtime_checkable
class RateLimiterPort(Protocol):
    """Port for rate limiting API requests.

    Implements token bucket or similar algorithm to enforce
    provider-specific rate limits (RULES.md §5.1).

    Note: Uses async methods as rate limiting may require
    waiting for token availability.

    Example:
        >>> limiter: RateLimiterPort = TokenBucketRateLimiter(rate=5.0, capacity=10)
        >>> await limiter.acquire()  # Wait for token
        >>> await limiter.acquire(tokens=2)  # Acquire multiple tokens
    """

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (default: 1)

        Raises:
            ValueError: If tokens > capacity
        """
        ...

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without waiting.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if acquired, False otherwise
        """
        ...

    def available_tokens(self) -> int:
        """Return current available tokens.

        Returns:
            Number of tokens available for immediate acquisition
        """
        ...


@runtime_checkable
class CircuitBreakerPort(Protocol):
    """Port for circuit breaker fault tolerance pattern.

    Implements RULES.md §3.1.4 circuit breaker requirements:
    - State machine: CLOSED -> OPEN (after failures) -> HALF_OPEN -> CLOSED
    - Configurable failure threshold (default: 5 consecutive errors)
    - Configurable recovery timeout (default: 5 minutes)

    Example:
        >>> breaker: CircuitBreakerPort = CircuitBreakerGuard(provider="chembl")
        >>> result = await breaker.call(async_func, arg1, arg2)
    """

    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state.

        Returns:
            Current state: CLOSED, OPEN, or HALF_OPEN
        """
        ...

    def get_failure_count(self) -> int:
        """Get current failure count.

        Returns:
            Number of consecutive failures
        """
        ...

    def get_recovery_timeout(self) -> float:
        """Seconds to wait in OPEN before a HALF_OPEN probe is allowed."""
        ...

    def get_last_failure_time(self) -> float | None:
        """Monotonic timestamp of the last recorded failure, if any."""
        ...

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
        ...

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state.

        Resets failure count and state. Use with caution
        as it bypasses normal recovery logic.
        """
        ...
