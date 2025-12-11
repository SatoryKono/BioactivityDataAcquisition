"""Resilience strategies and error classification ports for clients."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Protocol

from bioetl.domain.configs import HttpClientConfig


class ErrorCategory(str, Enum):
    """Unified error categories for client responses."""

    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    CLIENT_ERROR = "client_error"
    SUCCESS = "success"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RequestContext:
    """Context information for outbound requests."""

    provider: str
    endpoint: str
    status_code: int | None
    method: str = "GET"
    response_body: str | None = None


class ErrorClassifierPortABC(Protocol):
    """Contract for mapping raw responses to canonical error categories."""

    def classify(self, status_code: int | None) -> ErrorCategory:
        """Return error category for a given HTTP status code."""


@dataclass(frozen=True)
class BackoffStrategy:
    """Retry/backoff settings for resilient clients."""

    max_attempts: int
    backoff_factor: float
    backoff_max: float | None
    retry_statuses: tuple[int, ...]
    retry_exceptions: tuple[type[Exception], ...]


@dataclass(frozen=True)
class RateLimitStrategy:
    """Rate limiting parameters for proactive throttling."""

    rate_limit_per_sec: float


@dataclass(frozen=True)
class ClientResilienceStrategy:
    """Aggregate resilience configuration for infrastructure clients."""

    backoff: BackoffStrategy
    rate_limit: RateLimitStrategy
    error_classifier: ErrorClassifierPortABC

    @classmethod
    def from_http_config(
        cls,
        config: HttpClientConfig,
        *,
        classifier: ErrorClassifierPortABC,
        retry_exceptions: Iterable[type[Exception]] | None = None,
    ) -> "ClientResilienceStrategy":
        """Construct strategy from ``HttpClientConfig`` values."""

        retry_statuses = tuple(config.retry_on_status)
        retry_exceptions_tuple = tuple(retry_exceptions or ())

        backoff = BackoffStrategy(
            max_attempts=max(1, int(config.max_retries) + 1),
            backoff_factor=float(config.backoff_factor),
            backoff_max=float(config.backoff_max),
            retry_statuses=retry_statuses,
            retry_exceptions=retry_exceptions_tuple,
        )
        rate_limit = RateLimitStrategy(rate_limit_per_sec=float(config.rate_limit_per_sec))
        return cls(backoff=backoff, rate_limit=rate_limit, error_classifier=classifier)

