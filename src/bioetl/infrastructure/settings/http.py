"""HTTP client settings: timeouts, retry configuration, connection pool.

This module consolidates all HTTP-related constants that were previously
scattered across multiple infrastructure modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import requests

from bioetl.infrastructure.errors import ApiClientError, ApiTimeoutError


@dataclass(frozen=True, slots=True)
class HttpTimeouts:
    """HTTP timeout configuration.

    All values are in seconds.
    """

    connect: float = 10.0
    """Connection timeout in seconds."""

    read: float = 30.0
    """Read timeout in seconds."""

    total: float = 30.0
    """Total request timeout in seconds (default for single requests)."""


@dataclass(frozen=True, slots=True)
class RetrySettings:
    """Retry policy settings for HTTP clients.

    Defines default values for retry behavior including which HTTP status codes
    and exception types should trigger retries.
    """

    max_attempts: int = 4
    """Maximum number of retry attempts (including initial request)."""

    backoff_factor: float = 2.0
    """Multiplier for exponential backoff delay."""

    backoff_max: float = 60.0
    """Maximum backoff delay in seconds."""

    retry_statuses: frozenset[int] = frozenset({429, 500, 502, 503, 504})
    """HTTP status codes that should trigger a retry."""

    @property
    def retry_exceptions(self) -> tuple[type[Exception], ...]:
        """Exception types that should trigger a retry.

        Returns a fresh tuple each time to avoid mutation issues.
        """
        return (
            ApiTimeoutError,
            ApiClientError,
            requests.Timeout,
            requests.ConnectionError,
            requests.HTTPError,
            requests.RequestException,
        )


@dataclass(frozen=True, slots=True)
class ConnectionPoolSettings:
    """HTTP connection pool settings.

    Settings for managing connection pooling and rate limiting.
    """

    rate_limit_per_sec: float = 2.5
    """Maximum requests per second."""

    pool_connections: int = 10
    """Number of connection pools to cache."""

    pool_maxsize: int = 10
    """Maximum number of connections to save in the pool."""

    pool_block: bool = False
    """Whether to block when no connections are available."""


# Default instances for convenient access
DEFAULT_TIMEOUTS: Final[HttpTimeouts] = HttpTimeouts()
DEFAULT_RETRY: Final[RetrySettings] = RetrySettings()
DEFAULT_POOL: Final[ConnectionPoolSettings] = ConnectionPoolSettings()


__all__ = [
    "HttpTimeouts",
    "RetrySettings",
    "ConnectionPoolSettings",
    "DEFAULT_TIMEOUTS",
    "DEFAULT_RETRY",
    "DEFAULT_POOL",
]
