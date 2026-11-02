"""Timeout and circuit breaker network exceptions.

Covers request timeouts and circuit breaker protection.

All exceptions inherit from RecoverableError, indicating that
retry with exponential backoff is appropriate (per RULES.md §3.1.3).
"""

from __future__ import annotations

from bioetl.domain.exceptions.base import RecoverableError
from bioetl.domain.types import ErrorType

__all__ = [
    "CircuitBreakerOpenError",
    "TimeoutError",
]


class TimeoutError(RecoverableError):
    """Raised when request times out (502, 504, gateway errors).

    The request may be retried after a delay with exponential backoff.

    Attributes:
        timeout_seconds: Optional timeout duration that was exceeded.

    Example:
        >>> raise TimeoutError("Request to ChEMBL API timed out", timeout_seconds=30.0)
    """

    error_type = ErrorType.TIMEOUT

    def __init__(self, message: str, timeout_seconds: float | None = None) -> None:
        """Initialize TimeoutError.

        Args:
            message: Description of the timeout.
            timeout_seconds: Optional timeout duration that was exceeded.
        """
        self.timeout_seconds = timeout_seconds
        msg = message
        if timeout_seconds:
            msg += f" (timeout: {timeout_seconds}s)"
        super().__init__(msg)


class CircuitBreakerOpenError(RecoverableError):
    """Raised when circuit breaker is open and blocking requests.

    This indicates that the service has failed repeatedly and the circuit breaker
    has opened to prevent further requests. See ADR-007 for circuit breaker details.

    Attributes:
        provider: Name of the provider whose circuit breaker is open.
        retry_after: Seconds to wait before circuit breaker may close.

    Example:
        >>> raise CircuitBreakerOpenError("pubchem", retry_after=300.0)
    """

    error_type = ErrorType.TIMEOUT

    def __init__(self, provider: str, retry_after: float) -> None:
        """Initialize CircuitBreakerOpenError.

        Args:
            provider: Name of the provider whose circuit breaker is open.
            retry_after: Seconds to wait before circuit breaker may close.
        """
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker open for {provider}. Retry after {retry_after}s"
        )
