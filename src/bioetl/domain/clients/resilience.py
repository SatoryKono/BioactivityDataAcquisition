"""Resilience contracts for external clients.

This module defines policies and contracts for resilient communication
with external services, including retry logic, timeouts, and circuit
breaker patterns.

These contracts enable consistent error handling across all external
client implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    """Policy for retry behavior.

    Defines how retries should be handled for transient failures.
    Uses exponential backoff by default.

    Attributes:
        max_attempts: Maximum number of retry attempts.
        base_delay_seconds: Initial delay between retries.
        max_delay_seconds: Maximum delay between retries.
        exponential_base: Base for exponential backoff calculation.
        retryable_exceptions: Tuple of exception types to retry.

    Example:
        >>> policy = RetryPolicy(max_attempts=3, base_delay_seconds=1.0)
        >>> # Delay sequence: 1s, 2s, 4s (exponential)
    """

    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    retryable_exceptions: tuple[type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
    )

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number.

        Args:
            attempt: Current attempt number (1-based).

        Returns:
            Delay in seconds before next retry.
        """
        delay = self.base_delay_seconds * (self.exponential_base ** (attempt - 1))
        return min(delay, self.max_delay_seconds)

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Determine if retry should be attempted.

        Args:
            attempt: Current attempt number (1-based).
            exception: Exception that occurred.

        Returns:
            True if retry should be attempted.
        """
        if attempt >= self.max_attempts:
            return False
        return isinstance(exception, self.retryable_exceptions)


@dataclass(frozen=True)
class TimeoutPolicy:
    """Policy for timeout behavior.

    Defines various timeout thresholds for network operations.

    Attributes:
        connect_timeout_seconds: Timeout for establishing connection.
        read_timeout_seconds: Timeout for reading response.
        total_timeout_seconds: Total operation timeout.
    """

    connect_timeout_seconds: float = 10.0
    read_timeout_seconds: float = 30.0
    total_timeout_seconds: float = 300.0

    @property
    def as_tuple(self) -> tuple[float, float]:
        """Return timeout as (connect, read) tuple for requests library."""
        return (self.connect_timeout_seconds, self.read_timeout_seconds)


@dataclass(frozen=True)
class CircuitBreakerPolicy:
    """Policy for circuit breaker behavior.

    Implements the circuit breaker pattern to prevent cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failures exceeded threshold, requests fail immediately
    - HALF_OPEN: Testing if service recovered

    Attributes:
        failure_threshold: Number of failures to trip breaker.
        recovery_timeout_seconds: Time before attempting recovery.
        half_open_requests: Requests allowed in half-open state.
    """

    failure_threshold: int = 5
    recovery_timeout_seconds: float = 60.0
    half_open_requests: int = 3


@dataclass
class CircuitBreakerState:
    """Mutable state for circuit breaker.

    Tracks failures and state transitions for a circuit breaker instance.

    Attributes:
        failure_count: Current consecutive failure count.
        state: Current breaker state (closed, open, half_open).
        last_failure_time: Timestamp of last failure.
        half_open_successes: Successes in half-open state.
    """

    failure_count: int = 0
    state: str = "closed"  # closed, open, half_open
    last_failure_time: float | None = None
    half_open_successes: int = 0


class ResilientClientABC(ABC, Generic[T]):
    """Contract for resilient external client.

    Provides a wrapper for executing operations with retry and timeout
    handling. Implementations should use this to make external calls
    more robust.

    Example:
        >>> class HttpResilientClient(ResilientClientABC[Response]):
        ...     def execute_with_resilience(self, operation, **kwargs):
        ...         # Implement retry logic
        ...         ...
    """

    @abstractmethod
    def execute_with_resilience(
        self,
        operation: Callable[[], T],
        *,
        retry_policy: RetryPolicy | None = None,
        timeout_policy: TimeoutPolicy | None = None,
    ) -> T:
        """Execute operation with retry and timeout handling.

        Args:
            operation: Callable that performs the actual operation.
            retry_policy: Retry policy to use (or default).
            timeout_policy: Timeout policy to use (or default).

        Returns:
            Result of the operation.

        Raises:
            RetryExhaustedError: If all retries failed.
            TimeoutError: If operation exceeded timeout.
        """
        ...

    @abstractmethod
    def get_circuit_breaker_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state.

        Returns:
            Current state of the circuit breaker.
        """
        ...


class RetryExhaustedError(Exception):
    """Error raised when all retry attempts have failed."""

    def __init__(
        self,
        message: str,
        attempts: int,
        last_exception: Exception | None = None,
    ) -> None:
        """Initialize retry exhausted error.

        Args:
            message: Error description.
            attempts: Number of attempts made.
            last_exception: The last exception that occurred.
        """
        super().__init__(f"{message} after {attempts} attempts")
        self.attempts = attempts
        self.last_exception = last_exception


__all__ = [
    "CircuitBreakerPolicy",
    "CircuitBreakerState",
    "ResilientClientABC",
    "RetryExhaustedError",
    "RetryPolicy",
    "TimeoutPolicy",
]
