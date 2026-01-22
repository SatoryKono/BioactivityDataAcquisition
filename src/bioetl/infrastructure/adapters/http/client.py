"""Unified HTTP client with rate limiting.

Refactored to remove internal resilience logic (Retry, Circuit Breaker)
in favor of DataSourcePort decorators.

SRP Compliance:
- RateLimiterPort: Handles rate limiting (injected)
- UnifiedHTTPClient: Coordinates HTTP communication
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx

from bioetl.domain.ports import NoOpMetrics, NoOpTracing

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        LoggerPort,
        MetricsPort,
        RateLimiterPort,
        TracingPort,
    )
    from bioetl.domain.types import RunID


__all__ = [
    "UnifiedHTTPClient",
]


@dataclass
class UnifiedHTTPClient:
    """Async HTTP client with rate limiting and observability.

    Coordinates HTTP communication using injected rate limiter.
    Resilience (Retry, Circuit Breaker) is now handled by DataSourcePort decorators.

    Observability:
    - Creates tracing spans for all HTTP requests
    - Records metrics
    """

    rate_limiter: RateLimiterPort
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
        headers: dict[str, str] = {
            "User-Agent": user_agent,
            "Accept": "application/json",
        }
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

    def _record_request_metrics(
        self,
        method: str,
        duration: float,
        status_code: int,
        error: Exception | None,
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
        if error is not None or status_code >= 400:
            error_type = (
                type(error).__name__ if error else f"http_{status_code}"
            )
            self._metrics.increment_counter(
                "http_request_errors_total",
                1,
                {
                    "provider": self.provider,
                    "method": method.upper(),
                    "error_type": error_type,
                },
            )

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute request with rate limiting and observability."""
        client = self._get_client()
        start_time = time.perf_counter()
        status_code = 0
        error: Exception | None = None

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

        with span:
            try:
                # Rate Limiting
                await self.rate_limiter.acquire()

                # Execute
                response = await client.request(method, url, **kwargs)
                status_code = response.status_code
                response.raise_for_status()
                span.set_attribute("http.status_code", status_code)
                return response

            except Exception as e:
                error = e
                span.set_attribute("error", True)
                span.set_attribute("error.type", type(e).__name__)
                span.record_exception(e)
                raise

            finally:
                duration = time.perf_counter() - start_time
                span.set_attribute("bioetl.duration_ms", duration * 1000)
                self._record_request_metrics(method, duration, status_code, error)

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send GET request."""
        return await self._request("GET", url, params=params, headers=headers)

    async def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send POST request."""
        return await self._request("POST", url, json=json, data=data, headers=headers)

    async def head(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send HEAD request."""
        return await self._request("HEAD", url, headers=headers)

    async def get_once(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send single GET request.

        Same as get() now, as get() no longer retries.
        Kept for compatibility.
        """
        return await self.get(url, params=params, headers=headers)
