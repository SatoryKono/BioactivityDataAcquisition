"""Internal policy helpers for HTTP client retry orchestration."""

from __future__ import annotations

import httpx

from bioetl.domain.exceptions import RecoverableError
from bioetl.domain.ports import MetricsPort
from bioetl.domain.resilience import RetryConfig


def _can_retry(
    retry_config: RetryConfig,
    attempt: int,
    retries_used: int,
) -> bool:
    """Return True when another retry attempt is allowed."""
    if retry_config.is_last_attempt(attempt):
        return False
    return bool(retries_used < retry_config.effective_retry_budget())


def _record_request_metrics(
    metrics: MetricsPort | None,
    provider: str,
    method: str,
    duration: float,
    status_code: int,
    retries: int,
    last_error: Exception | None,
) -> None:
    """Record request duration, retry, and error metrics."""
    if metrics is None:
        return
    labels = {
        "provider": provider,
        "method": method.upper(),
        "status": str(status_code) if status_code else "error",
    }
    metrics.observe_histogram("bioetl_http_request_duration_seconds", duration, labels)
    if retries > 0:
        metrics.increment_counter(
            "bioetl_http_retries_total",
            retries,
            {"provider": provider, "method": method.upper()},
        )
    if last_error is not None or status_code >= 400:
        error_type = type(last_error).__name__ if last_error else f"http_{status_code}"
        metrics.increment_counter(
            "bioetl_http_request_errors_total",
            1,
            {
                "provider": provider,
                "method": method.upper(),
                "error_type": error_type,
            },
        )


def _status_code_from_error(exc: Exception) -> int:
    """Extract HTTP status code from retryable errors when available."""
    if isinstance(exc, httpx.HTTPStatusError):
        return int(exc.response.status_code)
    return 0


def _is_retryable_error(
    retry_config: RetryConfig,
    exc: Exception,
) -> bool:
    """Return True when exception is retryable by policy."""
    if isinstance(
        exc,
        httpx.TimeoutException
        | httpx.NetworkError
        | httpx.ProtocolError
        | httpx.ProxyError,
    ):
        return True
    if isinstance(exc, RecoverableError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return bool(retry_config.is_retryable_status(exc.response.status_code))
    return bool(retry_config.is_retryable_exception(exc))
