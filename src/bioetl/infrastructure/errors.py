"""Shared HTTP client error wrappers and helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import requests

from bioetl.domain.observability import LoggingPortABC

__all__ = [
    "ApiClientError",
    "ApiTimeoutError",
    "ApiParseError",
    "ApiUnexpectedStatusError",
    "wrap_http_errors",
]


class ApiClientError(Exception):
    """Base error for HTTP client failures."""

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        endpoint: str | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.endpoint = endpoint
        self.status_code = status_code
        self.cause = cause

    def __str__(self) -> str:
        base = self.__class__.__name__
        if self.provider:
            base += f" provider='{self.provider}'"
        if self.endpoint:
            base += f" endpoint='{self.endpoint}'"
        if self.status_code is not None:
            base += f" status={self.status_code}"
        return f"{base}: {self.args[0]}"


class ApiTimeoutError(ApiClientError):
    """Raised when an HTTP request exceeds the configured timeout."""


class ApiParseError(ApiClientError):
    """Raised when HTTP response payload cannot be parsed."""


class ApiUnexpectedStatusError(ApiClientError):
    """Raised when HTTP response contains an unexpected status code."""


@contextmanager
def wrap_http_errors(
    *,
    provider: str,
    endpoint: str | None = None,
    logger: LoggingPortABC | None = None,
) -> Iterator[dict[str, Any]]:
    """Context manager to standardize HTTP error handling and logging."""

    context: dict[str, Any] = {
        "provider": provider,
        "endpoint": endpoint,
        "status_code": None,
    }
    try:
        yield context
    except ApiClientError:
        raise
    except requests.Timeout as exc:
        _log_error("api_timeout_error", exc, context, logger)
        raise ApiTimeoutError(
            "HTTP request timed out",
            provider=provider,
            endpoint=endpoint,
            status_code=context["status_code"],
            cause=exc,
        ) from exc
    except requests.RequestException as exc:
        _log_error("api_request_error", exc, context, logger)
        raise ApiClientError(
            "HTTP request failed",
            provider=provider,
            endpoint=endpoint,
            status_code=context["status_code"],
            cause=exc,
        ) from exc
    except ValueError as exc:
        _log_error("api_parse_error", exc, context, logger)
        raise ApiParseError(
            "Failed to parse HTTP response",
            provider=provider,
            endpoint=endpoint,
            status_code=context["status_code"],
            cause=exc,
        ) from exc


def _log_error(
    event: str, exc: Exception, context: dict[str, Any], logger: LoggingPortABC | None
) -> None:
    if logger is None:
        return

    logger.error(
        event,
        provider=context.get("provider"),
        endpoint=context.get("endpoint"),
        status_code=context.get("status_code"),
        error=str(exc),
    )
