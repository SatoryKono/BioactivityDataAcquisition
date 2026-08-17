"""Internal flow helpers for HTTP client retry orchestration."""

from __future__ import annotations

from typing import Protocol

import httpx

from bioetl.domain.resilience import RetryConfig
from bioetl.infrastructure.adapters.decorators._retry_support import (
    _redact_transport_error_message,
)
from bioetl.infrastructure.adapters.http._client_retry_models import (
    _RequestAttemptOutcome,
)
from bioetl.infrastructure.adapters.http.client_retry_observability import (
    SpanLike,
    mark_span_error,
)


class _CanRetryCheck(Protocol):
    """Callable retry-budget check used by retry flow helpers."""

    def __call__(self, attempt: int, retries_used: int) -> bool: ...


class _RetryableErrorCheck(Protocol):
    """Callable retryable-error check used by retry flow helpers."""

    def __call__(self, exc: Exception) -> bool: ...


class _RetryDelayHandler(Protocol):
    """Callable retry-delay handler used by retry flow helpers."""

    async def __call__(
        self,
        attempt: int,
        url: str = "",
        response: httpx.Response | None = None,
    ) -> float: ...


class _RetryLogger(Protocol):
    """Callable structured retry logger used by retry flow helpers."""

    def __call__(
        self,
        url: str,
        method: str,
        attempt: int,
        wait_seconds: float,
        *,
        status_code: int | None = None,
        reason: str | None = None,
    ) -> None: ...


class _RetryBudgetRecorder(Protocol):
    """Callable retry-budget exhaustion recorder used by retry flow helpers."""

    def __call__(self, method: str, url: str) -> None: ...


class _StatusCodeResolver(Protocol):
    """Callable extracting status codes from retryable errors."""

    def __call__(self, exc: Exception) -> int: ...


def should_retry_response(
    retry_config: RetryConfig,
    can_retry: _CanRetryCheck,
    *,
    status_code: int,
    attempt: int,
    retries_used: int,
) -> bool:
    """Return True when a response should enter the retry path."""
    return retry_config.is_retryable_status(status_code) and can_retry(
        attempt,
        retries_used,
    )


def should_record_retry_budget_exhaustion(
    retry_config: RetryConfig,
    *,
    attempt: int,
) -> bool:
    """Return True when retry budget blocked a non-final retry opportunity."""
    return (
        retry_config.retry_budget_per_request is not None
        and not retry_config.is_last_attempt(attempt)
    )


async def handle_response_attempt(
    response: httpx.Response,
    *,
    method: str,
    url: str,
    attempt: int,
    retries_used: int,
    span: SpanLike,
    retry_config: RetryConfig,
    can_retry: _CanRetryCheck,
    handle_retry_delay: _RetryDelayHandler,
    log_retry: _RetryLogger,
) -> httpx.Response | _RequestAttemptOutcome:
    """Process a completed HTTP response without changing retry semantics."""
    if should_retry_response(
        retry_config,
        can_retry,
        status_code=response.status_code,
        attempt=attempt,
        retries_used=retries_used,
    ):
        status_code = response.status_code
        wait_seconds = await handle_retry_delay(attempt, url, response)
        log_retry(url, method, attempt, wait_seconds, status_code=status_code)
        status_error = httpx.HTTPStatusError(
            f"Server error {status_code}",
            request=response.request,
            response=response,
        )
        return _RequestAttemptOutcome(True, status_code, 1, status_error)

    response.raise_for_status()
    span.set_attribute("http.status_code", response.status_code)
    return response


async def handle_request_exception(
    exc: Exception,
    *,
    method: str,
    url: str,
    attempt: int,
    retries_used: int,
    span: SpanLike,
    retry_config: RetryConfig,
    is_retryable_error: _RetryableErrorCheck,
    can_retry: _CanRetryCheck,
    handle_retry_delay: _RetryDelayHandler,
    log_retry: _RetryLogger,
    record_retry_budget_exhausted: _RetryBudgetRecorder,
    status_code_from_error: _StatusCodeResolver,
) -> _RequestAttemptOutcome | None:
    """Process retryable vs terminal exception paths for one request attempt."""
    if not is_retryable_error(exc):
        mark_span_error(span, type(exc).__name__, exc)
        return None

    if can_retry(attempt, retries_used):
        wait_seconds = await handle_retry_delay(attempt, url)
        log_retry(
            url,
            method,
            attempt,
            wait_seconds,
            reason=_redact_transport_error_message(str(exc)),
        )
        return _RequestAttemptOutcome(
            True,
            status_code_from_error(exc),
            1,
            exc,
        )

    if should_record_retry_budget_exhaustion(retry_config, attempt=attempt):
        record_retry_budget_exhausted(method, url)

    return _RequestAttemptOutcome(
        False,
        status_code_from_error(exc),
        0,
        exc,
    )
