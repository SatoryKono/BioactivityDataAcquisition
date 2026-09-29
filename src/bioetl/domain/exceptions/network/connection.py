"""Connection and retry network exceptions.

Covers general network connectivity failures and retry exhaustion.

All exceptions inherit from RecoverableError, indicating that
retry with exponential backoff is appropriate (per RULES.md §3.1.3).
"""

from __future__ import annotations

import socket
from collections.abc import Iterator

from bioetl.domain.exceptions.base import RecoverableError
from bioetl.domain.types import ErrorType

__all__ = [
    "NetworkError",
    "RetryExhaustedError",
    "is_dns_resolution_failure",
]

_DNS_MESSAGE_MARKERS = (
    "getaddrinfo failed",
    "name or service not known",
    "nodename nor servname provided",
    "[errno 11001]",
    "[errno -2]",
    "[errno -3]",
    "temporary failure in name resolution",
)


def _iter_exception_chain(
    exc: BaseException | None, *, max_depth: int = 8
) -> Iterator[BaseException]:
    """Yield an exception chain following cause/context links."""
    current = exc
    depth = 0
    while current is not None and depth < max_depth:
        yield current
        current = current.__cause__ or current.__context__
        depth += 1


def _chain_texts(exc: BaseException | None, message: str | None) -> str:
    """Join the optional message with every chained exception message."""
    texts = [message] if message else []
    texts.extend(str(item) for item in _iter_exception_chain(exc))
    return " ".join(texts).lower()


def is_dns_resolution_failure(
    exc: BaseException | None = None,
    message: str | None = None,
) -> bool:
    """Return True when the failure is DNS resolution, not a transient TCP drop."""
    if any(
        isinstance(item, socket.gaierror)
        for item in _iter_exception_chain(exc)
    ):
        return True
    blob = _chain_texts(exc, message)
    return any(marker in blob for marker in _DNS_MESSAGE_MARKERS)


class NetworkError(RecoverableError):
    """Base class for network connectivity errors.

    This is a generic network error that may be retried.
    Covers connection failures, DNS issues, and general connectivity problems.

    Attributes:
        cause: Optional underlying exception that caused the network error.

    Example:
        >>> raise NetworkError("Connection refused", cause=original_exception)
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        """Initialize NetworkError.

        Args:
            message: Description of the network error.
            cause: Optional underlying exception.
        """
        self.cause = cause
        super().__init__(message)


class RetryExhaustedError(RecoverableError):
    """Raised when all retry attempts are exhausted.

    This indicates that a transient error persisted across all retry attempts.
    Further retries at the same operation are unlikely to succeed without
    external intervention.

    Attributes:
        url: URL or operation identifier that failed.
        attempts: Number of retry attempts made.
        last_error: Optional last exception from the final attempt.

    Example:
        >>> raise RetryExhaustedError(
        ...     "https://api.chembl.org/data",
        ...     attempts=3,
        ...     last_error=TimeoutError("Connection timed out")
        ... )
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(
        self, url: str, attempts: int, last_error: Exception | None = None
    ) -> None:
        """Initialize RetryExhaustedError.

        Args:
            url: URL or operation identifier that failed.
            attempts: Number of retry attempts made.
            last_error: Optional last exception from the final attempt.
        """
        self.url = url
        self.attempts = attempts
        self.last_error = last_error
        msg = f"Exhausted {attempts} retry attempts for {url}"
        if last_error:
            error_desc = str(last_error) or type(last_error).__name__
            msg += f": {error_desc}"
        super().__init__(msg)
