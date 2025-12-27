"""Unified HTTP client with rate limiting and circuit breaker.

Implements RULES.md Section 4.1 HTTP client requirements:
- Async support (httpx)
- Rate limiting (RateLimiterPort)
- Circuit breaker (CircuitBreakerPort)
- Exponential backoff with jitter (RetryPolicy)
- Observability via LoggerPort and MetricsPort (optional)

SRP Compliance:
- RateLimiterPort: Handles rate limiting (injected)
- CircuitBreakerPort: Handles fault tolerance (injected)
- RetryPolicy: Handles retry configuration (domain value object)
- LoggerPort: Handles structured logging (optional, injected)
- MetricsPort: Handles metrics collection (optional, injected)
- UnifiedHTTPClient: Coordinates HTTP communication
"""

from __future__ import annotations

import asyncio
import time
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import httpx

from bioetl.domain.exceptions import CircuitBreakerOpenError, RetryExhaustedError
from bioetl.domain.resilience import RetryPolicy

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        CircuitBreakerPort,
        LoggerPort,
        MetricsPort,
        RateLimiterPort,
    )
    from bioetl.domain.types import RunID


# Backward compatibility alias (deprecated)
RetryConfig = RetryPolicy


def _is_retryable_status(status_code: int) -> bool:
    """Check if HTTP status code is retryable."""
    return status_code in {429, 500, 502, 503, 504}


def _is_retryable_error(exc: Exception) -> bool:
    """Check if exception is retryable."""
    if isinstance(exc, httpx.ConnectError | httpx.ConnectTimeout | httpx.ReadTimeout):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return _is_retryable_status(exc.response.status_code)
    return False


@dataclass
class UnifiedHTTPClient:
    """Async HTTP client with rate limiting and circuit breaker.

    Coordinates HTTP communication using injected resilience components
    (SRP-compliant design).

    Args:
        rate_limiter: RateLimiterPort implementation for rate limiting
        circuit_breaker: CircuitBreakerPort implementation for fault tolerance
        retry_policy: RetryPolicy for exponential backoff configuration
        timeout: Request timeout in seconds (default: 30.0)
        run_id: Current run ID for correlation header
        user_agent: User-Agent string (default: "BioETL/5.0.0")
        contact_email: Optional contact email to append to User-Agent
        provider: Provider name for metrics labels (e.g., "chembl", "pubchem")
        logger: Optional LoggerPort for structured logging of retries/errors
        metrics: Optional MetricsPort for observability metrics

    Example:
        >>> from bioetl.infrastructure.adapters.http import TokenBucket, CircuitBreaker
        >>> bucket = TokenBucket(rate=5.0, capacity=5)
        >>> cb = CircuitBreaker(provider="chembl")
        >>> client = UnifiedHTTPClient(rate_limiter=bucket, circuit_breaker=cb)
        >>> async with client:
        ...     response = await client.get("https://api.example.com/data")

    Observability:
        When logger/metrics are provided, the client emits:
        - Logs: retry attempts, circuit breaker events, request completion
        - Metrics: http_request_latency_seconds, http_retries_total

    """

    rate_limiter: RateLimiterPort
    circuit_breaker: CircuitBreakerPort
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    timeout: float = 30.0
    run_id: RunID | None = None
    user_agent: str = "BioETL/5.0.0"
    contact_email: str | None = None
    provider: str = "unknown"
    logger: LoggerPort | None = None
    metrics: MetricsPort | None = None

    _client: httpx.AsyncClient | None = field(init=False, default=None)

    async def __aenter__(self) -> UnifiedHTTPClient:
        """Enter async context manager."""
        user_agent = self.user_agent
        if self.contact_email:
            user_agent = f"{user_agent} ({self.contact_email})"
        headers: dict[str, str] = {"User-Agent": user_agent}
        if self.run_id:
            headers["X-Correlation-ID"] = str(self.run_id)

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers=headers,
            follow_redirects=True,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get httpx client, raising if not in context."""
        if self._client is None:
            msg = "UnifiedHTTPClient must be used within async context manager"
            raise RuntimeError(msg)
        return self._client

    async def _handle_retry_delay(
        self,
        attempt: int,
        url: str = "",
        response: httpx.Response | None = None,
    ) -> None:
        """Calculate and sleep for the appropriate retry delay."""
        delay = self.retry_policy.calculate_delay(attempt, url)
        if response:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                with suppress(ValueError):
                    delay = float(retry_after)
        await asyncio.sleep(delay)

    def _get_status_class(self, status_code: int) -> str:
        """Get status class for metrics labels (2xx, 4xx, 5xx)."""
        return f"{status_code // 100}xx"

    def _get_host(self, url: str) -> str:
        """Extract host from URL for logging."""
        try:
            return urlparse(url).netloc or "unknown"
        except Exception:
            return "unknown"

    def _log_retry(
        self,
        attempt: int,
        url: str,
        reason: str,
        delay: float,
        status_code: int | None = None,
    ) -> None:
        """Log retry attempt if logger is available."""
        if self.logger:
            self.logger.warning(
                "HTTP request retry",
                provider=self.provider,
                host=self._get_host(url),
                method="GET",
                attempt=attempt + 1,
                max_attempts=self.retry_policy.max_attempts,
                reason=reason,
                status_code=status_code,
                delay_seconds=round(delay, 3),
            )

    def _record_request_metrics(
        self,
        method: str,
        status_code: int,
        duration: float,
        retries: int,
    ) -> None:
        """Record request metrics if metrics port is available."""
        if self.metrics:
            labels = {
                "provider": self.provider,
                "method": method,
                "status_class": self._get_status_class(status_code),
            }
            self.metrics.observe_histogram(
                "http_request_latency_seconds",
                duration,
                labels,
            )
            if retries > 0:
                self.metrics.increment_counter(
                    "http_retries_total",
                    retries,
                    {"provider": self.provider, "status_class": labels["status_class"]},
                )

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute request with retries and exponential backoff."""
        client = self._get_client()
        last_error: Exception | None = None
        retries = 0
        start_time = time.monotonic()

        for attempt in range(self.retry_policy.max_attempts):
            try:
                await self.rate_limiter.acquire()
                response = await self.circuit_breaker.call(
                    client.request, method, url, **kwargs
                )

                if _is_retryable_status(
                    response.status_code
                ) and not self.retry_policy.is_last_attempt(attempt):
                    retries += 1
                    delay = self.retry_policy.calculate_delay(attempt, url)
                    self._log_retry(
                        attempt,
                        url,
                        f"retryable status {response.status_code}",
                        delay,
                        response.status_code,
                    )
                    await self._handle_retry_delay(attempt, url, response)
                    continue

                response.raise_for_status()

                # Record successful request metrics
                duration = time.monotonic() - start_time
                self._record_request_metrics(method, response.status_code, duration, retries)

                return response

            except CircuitBreakerOpenError:
                # Log circuit breaker event
                if self.logger:
                    self.logger.error(
                        "Circuit breaker open",
                        provider=self.provider,
                        host=self._get_host(url),
                    )
                if self.metrics:
                    self.metrics.increment_counter(
                        "http_circuit_breaker_open_total",
                        1,
                        {"provider": self.provider},
                    )
                raise

            except Exception as exc:
                last_error = exc
                if not _is_retryable_error(exc):
                    # Log non-retryable error
                    if self.logger:
                        self.logger.error(
                            "HTTP request failed (non-retryable)",
                            provider=self.provider,
                            host=self._get_host(url),
                            error=str(exc),
                            error_type=type(exc).__name__,
                        )
                    raise

                if not self.retry_policy.is_last_attempt(attempt):
                    retries += 1
                    delay = self.retry_policy.calculate_delay(attempt, url)
                    self._log_retry(
                        attempt,
                        url,
                        f"{type(exc).__name__}: {exc}",
                        delay,
                    )
                    await self._handle_retry_delay(attempt, url)

        # Record failed request metrics
        duration = time.monotonic() - start_time
        self._record_request_metrics(method, 0, duration, retries)

        if self.logger:
            self.logger.error(
                "HTTP request failed after retries exhausted",
                provider=self.provider,
                host=self._get_host(url),
                total_attempts=self.retry_policy.max_attempts,
                total_duration_seconds=round(duration, 3),
            )

        raise RetryExhaustedError(url, self.retry_policy.max_attempts, last_error)

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send GET request.

        Args:
            url: Request URL
            params: Query parameters
            headers: Additional headers

        Returns:
            httpx.Response

        Raises:
            CircuitBreakerOpenError: If circuit is open
            RetryExhaustedError: If all retries exhausted
            httpx.HTTPStatusError: For non-retryable status codes

        """
        return await self._request_with_retry(
            "GET", url, params=params, headers=headers
        )

    async def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send POST request.

        Args:
            url: Request URL
            json: JSON body
            data: Form data
            headers: Additional headers

        Returns:
            httpx.Response

        """
        return await self._request_with_retry(
            "POST", url, json=json, data=data, headers=headers
        )

    async def head(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send HEAD request (for health checks).

        Args:
            url: Request URL
            headers: Additional headers

        Returns:
            httpx.Response

        """
        return await self._request_with_retry("HEAD", url, headers=headers)
