"""Shared helpers for HTTP adapter integration tests."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import MagicMock

from bioetl.domain.resilience import RetryConfig
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter

def build_mock_logger(*, bind_self: bool = False) -> MagicMock:
    """Create a mock logger with optional self-binding behavior."""
    logger = MagicMock()
    if bind_self:
        logger.bind = MagicMock(return_value=logger)
    return logger


def reset_http_client_state(client: UnifiedHTTPClient) -> None:
    """Reset mutable HTTP client state between tests sharing one client."""
    client.circuit_breaker.reset()
    rate_limiter = client.rate_limiter
    if isinstance(rate_limiter, TokenBucketRateLimiter):
        rate_limiter._tokens = float(rate_limiter.capacity)
        rate_limiter._last_refill = time.monotonic()


@asynccontextmanager
async def managed_http_client(
    *,
    provider: str,
    rate: float,
    capacity: float,
    limiter_provider: str | None = None,
    circuit_breaker_provider: str | None = None,
) -> AsyncIterator[UnifiedHTTPClient]:
    """Start and stop a shared HTTP client for integration tests."""
    client = UnifiedHTTPClient(
        rate_limiter=TokenBucketRateLimiter(
            rate=rate,
            capacity=capacity,
            provider=limiter_provider,
        ),
        circuit_breaker=CircuitBreakerGuard(
            provider=circuit_breaker_provider or provider
        ),
        retry_config=RetryConfig(
            base_delay=0.0,
            max_delay=0.0,
            multiplier=1.0,
            jitter_range=(0.0, 0.0),
        ),
        provider=provider,
    )
    await client.__aenter__()
    try:
        yield client
    finally:
        await client.__aexit__(None, None, None)
