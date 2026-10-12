# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Shared support for provider VCR rebalance integration tests."""

from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest

from bioetl.domain.resilience import RetryConfig
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter

REBALANCE_CASES = tuple(f"case_{index:02d}" for index in range(1, 16))
_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "vcr"


def build_vcr_config(provider: str) -> dict[str, Any]:
    """Build the canonical provider VCR config for rebalance suites."""
    return {
        "cassette_library_dir": str(_FIXTURES_DIR / provider),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query_ignore_email"],
        "decode_compressed_response": True,
    }


def build_rebalance_cassette_name(
    request: pytest.FixtureRequest,
    *,
    provider: str,
) -> str:
    """Return the deterministic cassette stem for one parameterized case."""
    case_id = request.node.callspec.id if hasattr(request.node, "callspec") else "case"
    return f"rf013_{provider}_health_{case_id}"


def reset_http_client_state(client: UnifiedHTTPClient) -> None:
    """Reset mutable HTTP client state between parameterized rebalance cases."""
    client.circuit_breaker.reset()
    rate_limiter = client.rate_limiter
    if isinstance(rate_limiter, TokenBucketRateLimiter):
        rate_limiter._tokens = float(rate_limiter.capacity)
        rate_limiter._last_refill = time.monotonic()


@asynccontextmanager
async def rebalance_http_client(
    *,
    provider: str,
    rate: float,
    capacity: int,
) -> AsyncIterator[UnifiedHTTPClient]:
    """Yield a deterministic HTTP client lifecycle for provider rebalance probes."""
    client = UnifiedHTTPClient(
        rate_limiter=TokenBucketRateLimiter(
            rate=rate,
            capacity=capacity,
            provider=f"{provider}_rf013",
        ),
        circuit_breaker=CircuitBreakerGuard(provider=f"{provider}_rf013"),
        retry_config=RetryConfig(
            base_delay=0.0,
            max_delay=0.0,
            multiplier=1.0,
            jitter_range=(0.0, 0.0),
        ),
        timeout=30.0,
        provider=provider,
    )
    await client.__aenter__()
    try:
        yield client
    finally:
        await client.__aexit__(None, None, None)
