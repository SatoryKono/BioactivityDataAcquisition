"""Retry request flow extracted from HTTPClientRetryMixin."""

from __future__ import annotations

import time
from typing import Any

import httpx

from bioetl.domain.exceptions import BioETLError, CircuitBreakerOpenError
from bioetl.infrastructure.adapters.http._client_retry_flow import (
    handle_request_exception,
    handle_response_attempt,
)
from bioetl.infrastructure.adapters.http._client_retry_models import (
    _RequestAttemptOutcome,
    _RetryRequestState,
)
from bioetl.infrastructure.adapters.http._client_retry_policy import (
    _is_retryable_error,
    _status_code_from_error,
)
from bioetl.infrastructure.adapters.http.client_retry_observability import (
    SpanLike,
    finalize_request_observability,
    handle_circuit_breaker_trip,
    raise_retry_exhausted,
    start_request_span,
)

__all__ = ["HTTPClientRetryRequestFlow"]


class HTTPClientRetryRequestFlow:
    """Request, attempt, and exception flow for the HTTP retry mixin."""

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
                allow_redirect_response=kwargs.get("follow_redirects") is False,
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
        allow_redirect_response: bool = False,
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
            allow_redirect_response=allow_redirect_response,
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
