"""Reusable retry policies for HTTP clients."""

from __future__ import annotations

import math
from typing import Iterable

from bioetl.domain.clients.base.contracts import RetryPolicyABC
from bioetl.infrastructure.errors import ApiClientError
from bioetl.infrastructure.settings.http import (
    DEFAULT_RETRY_EXCEPTIONS,
    DEFAULT_RETRY_STATUSES,
)


class ExponentialRetryPolicy(RetryPolicyABC):
    """Exponential backoff retry policy for HTTP clients.

    Implements configurable retry logic with exponential delay growth.
    Retries are triggered based on HTTP status codes or exception types.
    """

    def __init__(
        self,
        *,
        max_attempts: int,
        backoff_factor: float = 1.0,
        retry_statuses: Iterable[int] | None = None,
        retry_exceptions: tuple[type[Exception], ...] | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if backoff_factor < 0:
            raise ValueError("backoff_factor must be non-negative")

        self._max_attempts = int(max_attempts)
        self._backoff_factor = float(backoff_factor)
        self.retry_statuses = (
            set(retry_statuses) if retry_statuses else set(DEFAULT_RETRY_STATUSES)
        )
        self.retry_exceptions = retry_exceptions or DEFAULT_RETRY_EXCEPTIONS

    @property
    def max_attempts(self) -> int:
        """Maximum number of retry attempts."""
        return self._max_attempts

    @property
    def backoff_factor(self) -> float:
        """Delay multiplier between retry attempts."""
        return self._backoff_factor

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Check whether a retry should be attempted for the given exception.

        Args:
            exception: The exception that was raised.
            attempt: Current attempt number (1-indexed).

        Returns:
            True if retry should be attempted, False otherwise.
        """
        if attempt >= self.max_attempts:
            return False

        if isinstance(exception, self.retry_exceptions):
            return True

        if isinstance(exception, ApiClientError):
            status = getattr(exception, "status_code", None)
            if status is not None and status in self.retry_statuses:
                return True

            cause = getattr(exception, "cause", None)
            if isinstance(cause, self.retry_exceptions):
                return True

        status_code = _extract_status_code(exception)
        return status_code in self.retry_statuses if status_code is not None else False

    def get_backoff(self, attempt: int) -> float:
        """Calculate delay before the next retry attempt in seconds.

        Args:
            attempt: Current attempt number (1-indexed).

        Returns:
            Delay in seconds before next retry.
        """
        exponent = max(0, attempt - 1)
        return self.backoff_factor * math.pow(2.0, exponent)


def _extract_status_code(exc: Exception) -> int | None:
    """Extract HTTP status code from a requests exception.

    Args:
        exc: Exception that may contain a response object.

    Returns:
        HTTP status code if available, None otherwise.
    """
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if isinstance(status, int):
        return status
    return None
