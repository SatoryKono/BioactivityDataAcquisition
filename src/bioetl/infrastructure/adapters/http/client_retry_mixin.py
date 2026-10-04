# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Retry/backoff flow for UnifiedHTTPClient."""

from __future__ import annotations

import asyncio
from typing import Any, cast

import httpx

from bioetl.domain.ports import (
    CircuitBreakerPort,
    LoggerPort,
    MetricsPort,
    RateLimiterPort,
    TracingPort,
)
from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import RunID
from bioetl.infrastructure.adapters.http._client_retry_models import (
    _RequestAttemptOutcome,
    _RetryRequestState,
)
from bioetl.infrastructure.adapters.http._client_retry_policy import (
    _can_retry,
    _parse_retry_after,
    _record_request_metrics,
)
from bioetl.infrastructure.adapters.http._client_retry_request_flow import (
    HTTPClientRetryRequestFlow,
)
from bioetl.infrastructure.adapters.http.request_timing import execute_timed_request


class HTTPClientRetryMixin(HTTPClientRetryRequestFlow):
    """Retry policy orchestration extracted from UnifiedHTTPClient."""

    _request_not_before: float = 0.0

    retry_config: RetryConfig = cast(Any, None)  # Any: host attr default (PD6)
    _metrics: MetricsPort | None = cast(Any, None)  # Any: host attr default (PD6)
    provider: str = cast(Any, None)  # Any: host attr default (PD6)
    logger: LoggerPort | None = cast(Any, None)  # Any: host attr default (PD6)
    rate_limiter: RateLimiterPort = cast(Any, None)  # Any: host attr default (PD6)
    circuit_breaker: CircuitBreakerPort = cast(
        Any, None
    )  # Any: host attr default (PD6)
    _tracer: TracingPort | None = cast(Any, None)  # Any: host attr default (PD6)
    run_id: RunID | None = cast(Any, None)  # Any: host attr default (PD6)

    def _observability_run_id(self) -> str:
        return str(self.run_id) if self.run_id is not None else "unknown"

    def _get_client(self) -> httpx.AsyncClient:
        raise NotImplementedError

    async def _handle_retry_delay(
        self,
        attempt: int,
        url: str = "",
        response: httpx.Response | None = None,
    ) -> float:
        """Calculate and sleep for retry delay, honoring Retry-After."""
        delay = self.retry_config.calculate_delay(attempt, url)
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                retry_after_delay = _parse_retry_after(retry_after)
                if retry_after_delay is not None:
                    delay = self.retry_config.clamp_retry_after(retry_after_delay)
        if self.logger is not None:
            self.logger.info(
                "http_retry_wait",
                provider=self.provider,
                **({"run_id": str(self.run_id)} if self.run_id is not None else {}),
                attempt=attempt + 1,
                wait_seconds=float(delay),
                status_code=response.status_code if response is not None else None,
            )
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
                **({"run_id": str(self.run_id)} if self.run_id is not None else {}),
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
            **({"run_id": str(self.run_id)} if self.run_id is not None else {}),
        )

    async def _execute_single_attempt(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        attempt_number: int = 1,
        **kwargs: Any,  # Any: forwarding arbitrary request kwargs to underlying HTTP client
    ) -> httpx.Response:
        """Execute one rate-limited circuit-breaker guarded request."""
        return await execute_timed_request(
            self,
            method,
            lambda: client.request(method, url, **kwargs),
            attempt_number=attempt_number,
        )

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
