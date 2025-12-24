"""Unified HTTP client with rate limiting and circuit breaker.

Implements RULES.md Section 4.1 HTTP client requirements:
- Async support (httpx)
- Rate limiting (TokenBucket)
- Circuit breaker (fault tolerance)
- Exponential backoff with jitter
"""

from __future__ import annotations

import asyncio
import random
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx

from bioetl.domain.exceptions import CircuitBreakerOpenError, RetryExhaustedError

if TYPE_CHECKING:
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket


@dataclass
class RetryConfig:
    """Configuration for exponential backoff retry.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        multiplier: Delay multiplier per attempt (default: 2.0)
        jitter: Random jitter factor 0-1 (default: 0.1)
        deterministic: Use hash-based jitter for reproducibility (default: False)
        jitter_seed: Seed for deterministic jitter (default: None)

    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter: float = 0.1
    deterministic: bool = False
    jitter_seed: int | None = None

    def calculate_delay(self, attempt: int, url: str = "") -> float:
        """Calculate delay for given attempt number (0-indexed).

        Args:
            attempt: Attempt number (0-indexed)
            url: Request URL for deterministic jitter calculation

        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.multiplier**attempt)
        delay = min(delay, self.max_delay)

        jitter_range = delay * self.jitter
        if self.deterministic:
            # Hash-based deterministic jitter for reproducibility
            hash_input = f"{attempt}:{url}:{self.jitter_seed or 0}"
            jitter_factor = (hash(hash_input) % 1000) / 1000.0
            # Map 0.0-1.0 to -1.0 to +1.0
            delay += jitter_range * (jitter_factor * 2 - 1)
        else:
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0.0, delay)


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

    Combines httpx, TokenBucket rate limiter, and CircuitBreaker for
    resilient HTTP communication.

    Args:
        rate_limiter: TokenBucket for rate limiting
        circuit_breaker: CircuitBreaker for fault tolerance
        retry_config: RetryConfig for exponential backoff
        timeout: Request timeout in seconds (default: 30.0)
        run_id: Current run ID for correlation header
        user_agent: User-Agent string (default: "BioETL/5.0.0")
        contact_email: Optional contact email to append to User-Agent

    Example:
        >>> bucket = TokenBucket(rate=5.0, capacity=5)
        >>> cb = CircuitBreaker(provider="chembl")
        >>> client = UnifiedHTTPClient(rate_limiter=bucket, circuit_breaker=cb)
        >>> async with client:
        ...     response = await client.get("https://api.example.com/data")

    """

    rate_limiter: TokenBucket
    circuit_breaker: CircuitBreaker
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    timeout: float = 30.0
    run_id: RunID | None = None
    user_agent: str = "BioETL/5.0.0"
    contact_email: str | None = None

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
        delay = self.retry_config.calculate_delay(attempt, url)
        if response:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                with suppress(ValueError):
                    delay = float(retry_after)
        await asyncio.sleep(delay)

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute request with retries and exponential backoff."""
        client = self._get_client()
        last_error: Exception | None = None

        for attempt in range(self.retry_config.max_attempts):
            try:
                await self.rate_limiter.acquire()
                response = await self.circuit_breaker.call(
                    client.request, method, url, **kwargs
                )

                if (
                    _is_retryable_status(response.status_code)
                    and attempt < self.retry_config.max_attempts - 1
                ):
                    await self._handle_retry_delay(attempt, url, response)
                    continue

                response.raise_for_status()
                return response

            except CircuitBreakerOpenError:
                raise

            except Exception as exc:
                last_error = exc
                if not _is_retryable_error(exc):
                    raise

                if attempt < self.retry_config.max_attempts - 1:
                    await self._handle_retry_delay(attempt, url)

        raise RetryExhaustedError(url, self.retry_config.max_attempts, last_error)

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
