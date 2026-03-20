"""Retry/backoff and observability flow for UnifiedHTTPClient."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, NoReturn, Protocol, cast

import httpx

from bioetl.domain.exceptions import (
    BioETLError,
    CircuitBreakerOpenError,
    RecoverableError,
    RetryExhaustedError,
)
from bioetl.domain.ports import (
    CircuitBreakerPort,
    LoggerPort,
    MetricsPort,
    RateLimiterPort,
    TracingPort,
)
from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import RunID


class _SpanLike(Protocol):
    """Minimal span contract used by retry observability flow."""

    def __enter__(self) -> _SpanLike: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> object | None: ...

    def set_attribute(self, key: str, value: object) -> None: ...

    def record_exception(self, exception: Exception) -> None: ...


class _OtelTracerLike(Protocol):
    """Minimal tracer contract returned by TracingPort.get_tracer()."""

    def start_as_current_span(
        self,
        name: str,
        *,
        attributes: dict[str, object],
    ) -> _SpanLike: ...


@dataclass(frozen=True, slots=True)
class _RequestAttemptOutcome:
    """Retry-stage outcome for a single request attempt."""

    should_retry: bool
    status_code: int
    retries_increment: int
    last_error: Exception | None


@dataclass(slots=True)
class _RetryRequestState:
    """Mutable request-level retry state for the main retry loop."""

    status_code: int = 0
    retries: int = 0
    attempts_made: int = 0
    last_error: Exception | None = None

    def record_attempt(self, attempt: int) -> None:
        """Track the most recent attempt index as a 1-based count."""
        self.attempts_made = attempt + 1

    def apply_attempt_outcome(self, outcome: _RequestAttemptOutcome) -> bool:
        """Apply one retry outcome and report whether the loop should continue."""
        self.status_code = outcome.status_code
        self.retries += outcome.retries_increment
        self.last_error = outcome.last_error
        return outcome.should_retry


def _can_retry(
    retry_config: RetryConfig,
    attempt: int,
    retries_used: int,
) -> bool:
    """Return True when another retry attempt is allowed.

    Args:
        retry_config: Retry policy object with attempt and budget methods.
        attempt: Current attempt index (0-based).
        retries_used: Number of retries already consumed in this request.

    Returns:
        True if another attempt is permitted by attempt count and retry budget, False otherwise.
    """
    if retry_config.is_last_attempt(attempt):
        return False
    return retries_used < retry_config.effective_retry_budget()


def _record_request_metrics(
    metrics: MetricsPort,
    provider: str,
    method: str,
    duration: float,
    status_code: int,
    retries: int,
    last_error: Exception | None,
) -> None:
    """Record request duration, retry, and error metrics.

    Args:
        metrics: Metrics port for emitting counters and histograms.
        provider: Provider name used as label in metrics.
        method: HTTP method (GET, POST, etc.) used as label.
        duration: Total request duration in seconds.
        status_code: HTTP response status code (0 if connection-level error).
        retries: Number of retry attempts made.
        last_error: Final exception if the request failed, or None on success.
    """
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


def _status_code_from_error(exc: Exception) -> int:
    """Extract HTTP status code from retryable errors when available."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    return 0


class HTTPClientRetryMixin:
    """Retry policy orchestration extracted from UnifiedHTTPClient."""

    retry_config: RetryConfig
    _metrics: MetricsPort
    provider: str
    logger: LoggerPort | None
    rate_limiter: RateLimiterPort
    circuit_breaker: CircuitBreakerPort
    _tracer: TracingPort
    run_id: RunID | None

    def _get_client(self) -> httpx.AsyncClient:
        """Provided by HTTPClientContextMixin in UnifiedHTTPClient."""
        raise NotImplementedError

    def _start_request_span(
        self,
        method: str,
        url: str,
    ) -> _SpanLike:
        """Create and enter the request span for retry orchestration."""
        otel_tracer = cast(_OtelTracerLike, self._tracer.get_tracer("bioetl.http"))
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
        return span

    def _mark_span_error(
        self,
        span: _SpanLike,
        error_type: str,
        exc: Exception | None = None,
    ) -> None:
        """Mark span as failed and optionally record the triggering exception."""
        span.set_attribute("error", True)
        span.set_attribute("error.type", error_type)
        if exc is not None:
            span.record_exception(exc)

    def _finalize_request_observability(
        self,
        span: _SpanLike,
        retry_state: _RetryRequestState,
        *,
        method: str,
        start_time: float,
    ) -> None:
        """Finalize span and metrics for a completed request lifecycle."""
        duration = time.perf_counter() - start_time
        span.set_attribute("http.retries", retry_state.retries)
        span.set_attribute("bioetl.duration_ms", duration * 1000)
        span.__exit__(None, None, None)
        self._record_request_metrics(
            method,
            duration,
            retry_state.status_code,
            retry_state.retries,
            retry_state.last_error,
        )

    def _raise_retry_exhausted(
        self,
        url: str,
        retry_state: _RetryRequestState,
        span: _SpanLike,
    ) -> NoReturn:
        """Raise the terminal retry exhaustion error after span bookkeeping."""
        self._mark_span_error(span, "retry_exhausted", retry_state.last_error)
        raise RetryExhaustedError(
            url,
            retry_state.attempts_made,
            retry_state.last_error,
        )

    async def _handle_retry_delay(
        self,
        attempt: int,
        url: str = "",
        response: httpx.Response | None = None,
    ) -> float:
        """Calculate and sleep for retry delay, honoring Retry-After."""
        delay = self.retry_config.calculate_delay(attempt, url)
        if response:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                from contextlib import suppress

                with suppress(ValueError):
                    delay = self.retry_config.clamp_retry_after(float(retry_after))
        await asyncio.sleep(delay)
        return delay

    def _can_retry(
        self,
        attempt: int,
        retries_used: int,
    ) -> bool:
        """Backward-compatible wrapper for retry-budget decision logic."""
        return _can_retry(self.retry_config, attempt, retries_used)

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

    def _record_request_metrics(
        self,
        method: str,
        duration: float,
        status_code: int,
        retries: int,
        last_error: Exception | None,
    ) -> None:
        """Record request duration, retry, and error metrics via _metrics port."""
        _record_request_metrics(
            self._metrics,
            self.provider,
            method,
            duration,
            status_code,
            retries,
            last_error,
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
        """Execute one rate-limited circuit-breaker guarded request."""
        await self.rate_limiter.acquire()
        return await self.circuit_breaker.call(client.request, method, url, **kwargs)

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,  # Any: forwarding arbitrary request kwargs to underlying HTTP client
    ) -> httpx.Response:
        """Execute request with retries, backoff, and observability."""
        client = self._get_client()
        retry_state = _RetryRequestState()
        start_time = time.perf_counter()
        span = self._start_request_span(method, url)

        try:
            for attempt in range(self.retry_config.max_attempts):
                retry_state.record_attempt(attempt)
                result = await self._attempt_request(
                    client, method, url, attempt, retry_state.retries, span, kwargs
                )
                if isinstance(result, httpx.Response):
                    retry_state.status_code = result.status_code
                    return result

                if not retry_state.apply_attempt_outcome(result):
                    break

            self._raise_retry_exhausted(url, retry_state, span)
        finally:
            self._finalize_request_observability(
                span,
                retry_state,
                method=method,
                start_time=start_time,
            )

    def _is_retryable_error(
        self,
        exc: Exception,
    ) -> bool:
        """Return True when exception is retryable by policy."""
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
        span: _SpanLike,
        kwargs: dict[
            str, Any  # Any: dynamic payload or structural mixin boundary
        ],  # Any: forwarding arbitrary request kwargs to underlying HTTP client
    ) -> httpx.Response | _RequestAttemptOutcome:
        """Execute one request attempt and return response or retry decision."""
        try:
            response = await self._execute_single_attempt(client, method, url, **kwargs)
            return await self._handle_response_attempt(
                response,
                method=method,
                url=url,
                attempt=attempt,
                retries_used=retries_used,
                span=span,
            )

        except CircuitBreakerOpenError as exc:
            self._handle_circuit_breaker_open(exc, method=method, url=url, span=span)
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
            outcome = await self._handle_request_exception(
                exc,
                method=method,
                url=url,
                attempt=attempt,
                retries_used=retries_used,
                span=span,
            )
            if outcome is None:
                raise
            return outcome

    async def _handle_response_attempt(
        self,
        response: httpx.Response,
        *,
        method: str,
        url: str,
        attempt: int,
        retries_used: int,
        span: _SpanLike,
    ) -> httpx.Response | _RequestAttemptOutcome:
        """Process a completed HTTP response without changing retry semantics."""
        status_code = response.status_code

        if self.retry_config.is_retryable_status(status_code) and _can_retry(
            self.retry_config,
            attempt,
            retries_used,
        ):
            wait_seconds = await self._handle_retry_delay(attempt, url, response)
            self._log_retry(url, method, attempt, wait_seconds, status_code=status_code)
            status_error = httpx.HTTPStatusError(
                f"Server error {status_code}",
                request=response.request,
                response=response,
            )
            return _RequestAttemptOutcome(True, status_code, 1, status_error)

        response.raise_for_status()
        span.set_attribute("http.status_code", status_code)
        return response

    def _handle_circuit_breaker_open(
        self,
        exc: CircuitBreakerOpenError,
        *,
        method: str,
        url: str,
        span: _SpanLike,
    ) -> None:
        """Record circuit-breaker open state without altering propagation semantics."""
        self._mark_span_error(span, "circuit_breaker_open", exc)
        if self.logger:
            self.logger.warning(
                "http_circuit_breaker_open",
                url=url,
                method=method,
                provider=self.provider,
                retry_after=exc.retry_after,
            )

    async def _handle_request_exception(
        self,
        exc: Exception,
        *,
        method: str,
        url: str,
        attempt: int,
        retries_used: int,
        span: _SpanLike,
    ) -> _RequestAttemptOutcome | None:
        """Process retryable vs terminal exception paths for one request attempt."""
        if not self._is_retryable_error(exc):
            self._mark_span_error(span, type(exc).__name__, exc)
            return None

        if _can_retry(self.retry_config, attempt, retries_used):
            wait_seconds = await self._handle_retry_delay(attempt, url)
            self._log_retry(url, method, attempt, wait_seconds, reason=str(exc))
            return _RequestAttemptOutcome(
                True,
                _status_code_from_error(exc),
                1,
                exc,
            )

        if (
            self.retry_config.retry_budget_per_request is not None
            and not self.retry_config.is_last_attempt(attempt)
        ):
            self._record_retry_budget_exhausted(method, url)
        return _RequestAttemptOutcome(
            False,
            _status_code_from_error(exc),
            0,
            exc,
        )
