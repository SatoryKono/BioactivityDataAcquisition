# pyright: reportUninitializedInstanceVariable=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Retry/backoff flow for UnifiedHTTPClient."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from bioetl.domain.exceptions import BioETLError, CircuitBreakerOpenError
from bioetl.domain.ports import (
    CircuitBreakerPort,
    LoggerPort,
    MetricsPort,
    RateLimiterPort,
    TracingPort,
)
from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import RunID
from bioetl.infrastructure.adapters.http._client_retry_flow import (
    handle_request_exception,
    handle_response_attempt,
)
from bioetl.infrastructure.adapters.http._client_retry_models import (
    _RequestAttemptOutcome,
    _RetryRequestState,
)
from bioetl.infrastructure.adapters.http._client_retry_policy import (
    _can_retry,
    _is_retryable_error,
    _record_request_metrics,
    _status_code_from_error,
)
from bioetl.infrastructure.adapters.http.client_retry_observability import (
    SpanLike,
    finalize_request_observability,
    handle_circuit_breaker_trip,
    raise_retry_exhausted,
    start_request_span,
)


class HTTPClientRetryMixin:
    """Retry policy orchestration extracted from UnifiedHTTPClient."""

    retry_config: RetryConfig
    _metrics: MetricsPort | None
    provider: str
    logger: LoggerPort | None
    rate_limiter: RateLimiterPort
    circuit_breaker: CircuitBreakerPort
    _tracer: TracingPort | None
    run_id: RunID | None

    def _observability_run_id(self) -> str:
        """Return a stable run identifier for retry logs and spans."""
        return str(self.run_id) if self.run_id is not None else "unknown"

    def _get_client(self) -> httpx.AsyncClient:
        """Provided by HTTPClientContextMixin in UnifiedHTTPClient."""
        raise NotImplementedError

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
        return float(delay)

    def _can_retry(self, attempt: int, retries_used: int) -> bool:
        """Check if retry is allowed based on retry budget and attempt count."""
        return _can_retry(self.retry_config, attempt, retries_used)

    def _record_retry_budget_exhausted(self, method: str, url: str) -> None:
        """Emit retry-budget exhaustion metrics and warning log."""
        if self._metrics is not None:
            self._metrics.increment_counter(
                "bioetl_http_retry_budget_exhausted_total",
                1,
                {"provider": self.provider, "method": method.upper()},
            )
        if self.logger:
            self.logger.warning(
                "http_retry_budget_exhausted",
                provider=self.provider,
                run_id=self._observability_run_id(),
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
            run_id=self._observability_run_id(),
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

    def _should_continue_retry(
        self,
        result: httpx.Response | _RequestAttemptOutcome,
        retry_state: _RetryRequestState,
    ) -> bool:
        """Determine if retry should continue based on attempt outcome.

        Args:
            result: The outcome of the current attempt
            retry_state: Current retry state

        Returns:
            True if retry should continue, False to break retry loop
        """
        if isinstance(result, httpx.Response):
            retry_state.status_code = result.status_code
            return False  # Success - return the response

        # Apply retry outcome logic
        return retry_state.apply_attempt_outcome(result)

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
        span = start_request_span(
            self._tracer,
            provider=self.provider,
            run_id=self.run_id,
            method=method,
            url=url,
        )

        try:
            for attempt in range(self.retry_config.max_attempts):
                retry_state.record_attempt(attempt)
                result = await self._attempt_request(
                    client, method, url, attempt, retry_state.retries, span, kwargs
                )
                if not self._should_continue_retry(result, retry_state):
                    if isinstance(result, httpx.Response):
                        return result
                    break
            raise_retry_exhausted(url, retry_state, span)
        finally:
            finalize_request_observability(
                span,
                retry_state,
                method=method,
                start_time=start_time,
                record_metrics=self._record_request_metrics,
            )

    def _is_retryable_error(self, exc: Exception) -> bool:
        """Check if the given exception is retryable according to retry policy."""
        return _is_retryable_error(self.retry_config, exc)

    async def _attempt_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        attempt: int,
        retries_used: int,
        span: SpanLike,
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
            handle_circuit_breaker_trip(
                exc,
                method=method,
                url=url,
                span=span,
                provider=self.provider,
                run_id=self._observability_run_id(),
                logger=self.logger,
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
        span: SpanLike,
    ) -> httpx.Response | _RequestAttemptOutcome:
        """Process a completed HTTP response without changing retry semantics."""
        return await handle_response_attempt(
            response,
            method=method,
            url=url,
            attempt=attempt,
            retries_used=retries_used,
            span=span,
            retry_config=self.retry_config,
            can_retry=self._can_retry,
            handle_retry_delay=self._handle_retry_delay,
            log_retry=self._log_retry,
        )

    async def _handle_request_exception(
        self,
        exc: Exception,
        *,
        method: str,
        url: str,
        attempt: int,
        retries_used: int,
        span: SpanLike,
    ) -> _RequestAttemptOutcome | None:
        """Process retryable vs terminal exception paths for one request attempt."""
        return await handle_request_exception(
            exc,
            method=method,
            url=url,
            attempt=attempt,
            retries_used=retries_used,
            span=span,
            retry_config=self.retry_config,
            is_retryable_error=self._is_retryable_error,
            can_retry=self._can_retry,
            handle_retry_delay=self._handle_retry_delay,
            log_retry=self._log_retry,
            record_retry_budget_exhausted=self._record_retry_budget_exhausted,
            status_code_from_error=_status_code_from_error,
        )
