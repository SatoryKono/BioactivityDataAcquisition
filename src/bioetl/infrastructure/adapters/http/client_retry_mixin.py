# mypy: disable-error-code=attr-defined
# mypy: disable-error-code=no-any-return
"""Retry/backoff and observability flow for UnifiedHTTPClient."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

import httpx

from bioetl.domain.exceptions import (
    BioETLError,
    CircuitBreakerOpenError,
    RecoverableError,
    RetryExhaustedError,
)

if TYPE_CHECKING:
    from opentelemetry.trace import Span


def _can_retry(
    retry_config: Any,  # Any: concrete retry policy object
    attempt: int,
    retries_used: int,
) -> bool:
    """Return True when another retry attempt is allowed.

    Returns:
        True if another attempt is permitted by attempt count and retry budget, False otherwise.
    """
    if retry_config.is_last_attempt(attempt):
        return False
    return retries_used < retry_config.effective_retry_budget()


def _record_request_metrics(
    metrics: Any,  # Any: concrete metrics implementation
    provider: str,
    method: str,
    duration: float,
    status_code: int,
    retries: int,
    last_error: Exception | None,
) -> None:
    """Record request duration, retry, and error metrics."""
    labels = {
        "provider": provider,
        "method": method.upper(),
        "status": str(status_code) if status_code else "error",
    }
    metrics.observe_histogram("http_request_duration_seconds", duration, labels)
    if retries > 0:
        metrics.increment_counter(
            "http_retries_total",
            retries,
            {"provider": provider, "method": method.upper()},
        )
    if last_error is not None or status_code >= 400:
        error_type = type(last_error).__name__ if last_error else f"http_{status_code}"
        metrics.increment_counter(
            "http_request_errors_total",
            1,
            {
                "provider": provider,
                "method": method.upper(),
                "error_type": error_type,
            },
        )


class HTTPClientRetryMixin:
    """Retry policy orchestration extracted from UnifiedHTTPClient."""

    retry_config: Any  # Any: configured concrete retry policy object
    _metrics: Any  # Any: concrete metrics implementation
    provider: str
    logger: Any | None  # Any: logger interface varies by composition wiring
    rate_limiter: Any  # Any: async rate limiter port
    circuit_breaker: Any  # Any: circuit breaker port
    _tracer: Any  # Any: tracing port

    async def _handle_retry_delay(
        self,
        attempt: int,
        url: str = "",
        response: httpx.Response | None = None,
    ) -> float:
        """Calculate and sleep for retry delay, honoring Retry-After.

        Returns:
            Actual delay in seconds that was slept, after clamping Retry-After if present.
        """
        delay = self.retry_config.calculate_delay(attempt, url)
        if response:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                from contextlib import suppress

                with suppress(ValueError):
                    delay = self.retry_config.clamp_retry_after(float(retry_after))
        await asyncio.sleep(delay)
        return delay

    def _record_retry_budget_exhausted(
        self,
        method: str,
        url: str,
    ) -> None:
        """Emit retry-budget exhaustion metrics and warning log."""
        self._metrics.increment_counter(
            "http_retry_budget_exhausted_total",
            1,
            {"provider": self.provider, "method": method.upper()},
        )
        if self.logger:
            self.logger.warning(
                "http_retry_budget_exhausted",
                provider=self.provider,
                method=method,
                url=url,
                retry_budget=self.retry_config.effective_retry_budget(),
                max_attempts=self.retry_config.max_attempts,
            )

    def _log_retry(
        self,
        url: str,
        method: str,
        attempt: int,
        wait_seconds: float,
        *,
        status_code: int | None = None,
        reason: str | None = None,
    ) -> None:
        """Log structured retry event."""
        if not self.logger:
            return
        self.logger.warning(
            "Retrying request",
            stage="extract",
            attempt=attempt + 1,
            max_attempts=self.retry_config.max_attempts,
            wait_seconds=round(wait_seconds, 3),
            reason=reason or (f"HTTP {status_code}" if status_code else "unknown"),
            url=url,
            method=method,
            provider=self.provider,
        )

    async def _execute_single_attempt(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs: Any,  # Any: forwarding arbitrary request kwargs to underlying HTTP client
    ) -> httpx.Response:
        """Execute one rate-limited circuit-breaker guarded request.

        Returns:
            httpx.Response from the circuit-breaker guarded HTTP call.
        """
        await self.rate_limiter.acquire()
        return await self.circuit_breaker.call(client.request, method, url, **kwargs)

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,  # Any: forwarding arbitrary request kwargs to underlying HTTP client
    ) -> httpx.Response:
        """Execute request with retries, backoff, and observability.

        Returns:
            httpx.Response on success, raises RetryExhaustedError if all attempts fail.
        """
        client = self._get_client()
        last_error: Exception | None = None
        start_time = time.perf_counter()
        status_code = 0
        retries = 0
        attempts_made = 0

        otel_tracer = self._tracer.get_tracer("bioetl.http")
        span = otel_tracer.start_as_current_span(
            f"http.{method.lower()}",
            attributes={
                "http.method": method,
                "http.url": url,
                "bioetl.provider": self.provider,
                "bioetl.run_id": str(self.run_id) if self.run_id else "unknown",
            },
        )
        span.__enter__()

        try:
            for attempt in range(self.retry_config.max_attempts):
                attempts_made = attempt + 1
                result = await self._attempt_request(
                    client, method, url, attempt, retries, span, kwargs
                )
                if isinstance(result, httpx.Response):
                    status_code = result.status_code
                    return result

                should_retry, status_code, retries_inc, last_error = result
                retries += retries_inc
                if not should_retry:
                    break

            span.set_attribute("error", True)
            span.set_attribute("error.type", "retry_exhausted")
            if last_error:
                span.record_exception(last_error)
            raise RetryExhaustedError(url, attempts_made, last_error)
        finally:
            duration = time.perf_counter() - start_time
            span.set_attribute("http.retries", retries)
            span.set_attribute("bioetl.duration_ms", duration * 1000)
            span.__exit__(None, None, None)
            _record_request_metrics(
                self._metrics,
                self.provider,
                method,
                duration,
                status_code,
                retries,
                last_error,
            )

    def _is_retryable_error(
        self,
        exc: Exception,
    ) -> bool:
        """Return True when exception is retryable by policy.

        Returns:
            True if the exception type or HTTP status code is retryable per retry config, False otherwise.
        """
        if isinstance(
            exc,
            httpx.ConnectError
            | httpx.ConnectTimeout
            | httpx.ReadTimeout
            | httpx.ReadError
            | httpx.WriteError
            | httpx.ProtocolError
            | httpx.ProxyError,
        ):
            return True
        if isinstance(exc, RecoverableError):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return self.retry_config.is_retryable_status(exc.response.status_code)
        return self.retry_config.is_retryable_exception(exc)

    async def _attempt_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        attempt: int,
        retries_used: int,
        span: Span,
        kwargs: dict[
            str, Any  # Any: dynamic payload or structural mixin boundary
        ],  # Any: forwarding arbitrary request kwargs to underlying HTTP client
    ) -> httpx.Response | tuple[bool, int, int, Exception | None]:
        """Execute one request attempt and return response or retry decision.

        Returns:
            httpx.Response on success, or tuple of (should_retry, status_code, retries_increment, exception) on failure.
        """
        try:
            response = await self._execute_single_attempt(client, method, url, **kwargs)
            status_code = response.status_code

            if self.retry_config.is_retryable_status(status_code) and _can_retry(
                self.retry_config,
                attempt,
                retries_used,
            ):
                wait_seconds = await self._handle_retry_delay(attempt, url, response)
                self._log_retry(
                    url, method, attempt, wait_seconds, status_code=status_code
                )
                return (True, status_code, 1, None)

            response.raise_for_status()
            span.set_attribute("http.status_code", status_code)
            return response

        except CircuitBreakerOpenError as exc:
            span.set_attribute("error", True)
            span.set_attribute("error.type", "circuit_breaker_open")
            span.record_exception(exc)
            if self.logger:
                self.logger.warning(
                    "http_circuit_breaker_open",
                    url=url,
                    method=method,
                    provider=self.provider,
                    retry_after=exc.retry_after,
                )
            raise

        except (
                BioETLError,
                ConnectionError,
                OSError,
                RuntimeError,
                TimeoutError,
                ValueError,
                httpx.HTTPError,
        ) as exc:
            if not self._is_retryable_error(exc):
                span.set_attribute("error", True)
                span.set_attribute("error.type", type(exc).__name__)
                span.record_exception(exc)
                raise

            if _can_retry(self.retry_config, attempt, retries_used):
                wait_seconds = await self._handle_retry_delay(attempt, url)
                self._log_retry(url, method, attempt, wait_seconds, reason=str(exc))
                status_code = (
                    exc.response.status_code
                    if isinstance(exc, httpx.HTTPStatusError)
                    else 0
                )
                return (True, status_code, 1, exc)

            if (
                self.retry_config.retry_budget_per_request is not None
                and not self.retry_config.is_last_attempt(attempt)
            ):
                self._record_retry_budget_exhausted(method, url)
            status_code = (
                exc.response.status_code
                if isinstance(exc, httpx.HTTPStatusError)
                else 0
            )
            return (False, status_code, 0, exc)
