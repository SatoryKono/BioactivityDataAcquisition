"""Unified HTTP client with rate limiting and circuit breaker.

Implements RULES.md Section 4.1 HTTP client requirements:
- Async support (httpx)
- Rate limiting (RateLimiterPort)
- Circuit breaker (CircuitBreakerPort)
- Exponential backoff with jitter (RetryPolicy)

SRP Compliance:
- RateLimiterPort: Handles rate limiting (injected)
- CircuitBreakerPort: Handles fault tolerance (injected)
- RetryPolicy: Handles retry configuration (domain value object)
- UnifiedHTTPClient: Coordinates HTTP communication
"""

from __future__ import annotations

import asyncio
import time
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx

from bioetl.domain.exceptions import CircuitBreakerOpenError, RetryExhaustedError
from bioetl.domain.ports import NoOpMetrics, NoOpTracing
from bioetl.domain.resilience import RetryPolicy

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        CircuitBreakerPort,
        LoggerPort,
        MetricsPort,
        RateLimiterPort,
        TracingPort,
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
    """Async HTTP client with rate limiting, circuit breaker, and observability.

    Coordinates HTTP communication using injected resilience and observability
    components (SRP-compliant design).

    Observability (Phase 1 Refactoring):
    - Creates tracing spans for all HTTP requests with method/URL/status attributes
    - Records http_request_duration_seconds histogram by provider/method/status
    - Increments http_request_errors_total counter on failures
    - Logs circuit breaker state changes and retry attempts

    Args:
        rate_limiter: RateLimiterPort implementation for rate limiting
        circuit_breaker: CircuitBreakerPort implementation for fault tolerance
        retry_policy: RetryPolicy for exponential backoff configuration
        timeout: Request timeout in seconds (default: 30.0)
        run_id: Current run ID for correlation header
        user_agent: User-Agent string (default: "BioETL/5.0.0")
        contact_email: Optional contact email to append to User-Agent
        provider: Provider name for metrics labels (default: "unknown")
        tracer: TracingPort for distributed tracing (default: NoOpTracing)
        metrics: MetricsPort for metrics collection (default: NoOpMetrics)
        logger: LoggerPort for structured logging (optional)

    Example:
        >>> from bioetl.infrastructure.adapters.http import TokenBucket, CircuitBreaker
        >>> bucket = TokenBucket(rate=5.0, capacity=5)
        >>> cb = CircuitBreaker(provider="chembl")
        >>> client = UnifiedHTTPClient(rate_limiter=bucket, circuit_breaker=cb)
        >>> async with client:
        ...     response = await client.get("https://api.example.com/data")

    """

    rate_limiter: RateLimiterPort
    circuit_breaker: CircuitBreakerPort
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    timeout: float = 30.0
    run_id: RunID | None = None
    user_agent: str = "BioETL/5.0.0"
    contact_email: str | None = None
    provider: str = "unknown"
    tracer: TracingPort | None = None
    metrics: MetricsPort | None = None
    logger: LoggerPort | None = None

    _client: httpx.AsyncClient | None = field(init=False, default=None)
    _tracer: TracingPort = field(init=False)
    _metrics: MetricsPort = field(init=False)

    def __post_init__(self) -> None:
        """Initialize observability components with defaults if not provided."""
        self._tracer = self.tracer if self.tracer is not None else NoOpTracing()
        self._metrics = self.metrics if self.metrics is not None else NoOpMetrics()

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

    def _record_request_metrics(
        self,
        method: str,
        duration: float,
        status_code: int,
        retries: int,
        last_error: Exception | None,
    ) -> None:
        """Record HTTP request metrics."""
        labels = {
            "provider": self.provider,
            "method": method.upper(),
            "status": str(status_code) if status_code else "error",
        }
        self._metrics.observe_histogram(
            "http_request_duration_seconds",
            duration,
            labels,
        )
        if retries > 0:
            self._metrics.increment_counter(
                "http_retries_total",
                retries,
                {"provider": self.provider, "method": method.upper()},
            )
        if last_error is not None or status_code >= 400:
            error_type = (
                type(last_error).__name__ if last_error else f"http_{status_code}"
            )
            self._metrics.increment_counter(
                "http_request_errors_total",
                1,
                {"provider": self.provider, "method": method.upper(), "error_type": error_type},
            )

    def _log_retry(
        self, url: str, method: str, attempt: int, *, status_code: int | None = None, error: str | None = None
    ) -> None:
        """Log retry attempt if logger is configured."""
        if not self.logger:
            return
        kwargs: dict[str, Any] = {
            "url": url,
            "method": method,
            "attempt": attempt + 1,
            "provider": self.provider,
        }
        if status_code is not None:
            kwargs["status_code"] = status_code
        if error is not None:
            kwargs["error"] = error
        self.logger.debug("http_retry", **kwargs)

    async def _execute_single_attempt(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute a single HTTP request attempt."""
        await self.rate_limiter.acquire()
        return await self.circuit_breaker.call(client.request, method, url, **kwargs)

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute request with retries, exponential backoff, and observability.

        Creates a tracing span for the entire request lifecycle and records
        metrics for duration and errors.
        """
        client = self._get_client()
        last_error: Exception | None = None
        start_time = time.perf_counter()
        status_code = 0
        retries = 0

        # Start tracing span
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
            for attempt in range(self.retry_policy.max_attempts):
                result = await self._attempt_request(
                    client, method, url, attempt, span, kwargs
                )
                if isinstance(result, httpx.Response):
                    status_code = result.status_code
                    return result
                # Result is a tuple: (should_retry, status_code, retries_increment, error)
                should_retry, status_code, retries_inc, last_error = result
                retries += retries_inc
                if not should_retry:
                    break

            # All retries exhausted
            span.set_attribute("error", True)
            span.set_attribute("error.type", "retry_exhausted")
            if last_error:
                span.record_exception(last_error)
            raise RetryExhaustedError(url, self.retry_policy.max_attempts, last_error)

        finally:
            duration = time.perf_counter() - start_time
            span.set_attribute("http.retries", retries)
            span.set_attribute("bioetl.duration_ms", duration * 1000)
            span.__exit__(None, None, None)
            self._record_request_metrics(method, duration, status_code, retries, last_error)

    async def _attempt_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        attempt: int,
        span: Any,
        kwargs: dict[str, Any],
    ) -> httpx.Response | tuple[bool, int, int, Exception | None]:
        """Execute a single request attempt, returning response or retry info.

        Returns:
            Either httpx.Response on success, or a tuple of
            (should_retry, status_code, retries_increment, error) for retry handling.
        """
        try:
            response = await self._execute_single_attempt(client, method, url, **kwargs)
            status_code = response.status_code

            if _is_retryable_status(status_code) and not self.retry_policy.is_last_attempt(attempt):
                self._log_retry(url, method, attempt, status_code=status_code)
                await self._handle_retry_delay(attempt, url, response)
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
                    "http_circuit_breaker_open", url=url, method=method, provider=self.provider
                )
            raise

        except Exception as exc:
            if not _is_retryable_error(exc):
                span.set_attribute("error", True)
                span.set_attribute("error.type", type(exc).__name__)
                span.record_exception(exc)
                raise

            if not self.retry_policy.is_last_attempt(attempt):
                self._log_retry(url, method, attempt, error=str(exc))
                await self._handle_retry_delay(attempt, url)
            return (True, 0, 1, exc)

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
