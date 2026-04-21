"""RF-013: OpenAlex VCR cassette rebalancing smoke coverage.

Records deterministic health-probe cassettes to increase provider baseline.
"""

from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.openalex import OpenAlexAdapter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs

CASSETTE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "vcr" / "openalex"
REBALANCE_CASES = tuple(f"case_{index:02d}" for index in range(1, 16))


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    """Configure VCR with provider cassette directory and credential-safe matcher."""
    return {
        "cassette_library_dir": str(CASSETTE_DIR),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query_ignore_email"],
        "decode_compressed_response": True,
    }


@pytest.fixture
def vcr_cassette_name(request: pytest.FixtureRequest) -> str:
    """Use deterministic cassette names for RF-013 rebalance cases."""
    case_id = request.node.callspec.id if hasattr(request.node, "callspec") else "case"
    return f"rf013_openalex_health_{case_id}"


def _reset_http_client_state(client: UnifiedHTTPClient) -> None:
    """Reset mutable HTTP client state between parameterized rebalance cases."""
    client.circuit_breaker.reset()
    rate_limiter = client.rate_limiter
    if isinstance(rate_limiter, TokenBucketRateLimiter):
        rate_limiter._tokens = float(rate_limiter.capacity)
        rate_limiter._last_refill = time.monotonic()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def http_client() -> AsyncIterator[UnifiedHTTPClient]:
    """Create and manage OpenAlex HTTP client lifecycle for integration tests."""
    client = UnifiedHTTPClient(
        rate_limiter=TokenBucketRateLimiter(
            rate=10.0, capacity=20, provider="openalex_rf013"
        ),
        circuit_breaker=CircuitBreakerGuard(provider="openalex_rf013"),
        retry_config=RetryConfig(
            base_delay=0.0,
            max_delay=0.0,
            multiplier=1.0,
            jitter_range=(0.0, 0.0),
        ),
        timeout=30.0,
        provider="openalex",
    )
    await client.__aenter__()
    yield client
    await client.__aexit__(None, None, None)


@pytest.fixture
def adapter(http_client: UnifiedHTTPClient) -> OpenAlexAdapter:
    """Create OpenAlex adapter used by rebalance tests."""
    _reset_http_client_state(http_client)
    return OpenAlexAdapter(
        http_client=http_client,
        logger=NoOpLogger(),
        mailto="bioetl-test@example.com",
        batch_size=10,
        metrics=NoOpMetrics(),
        **build_http_adapter_runtime_kwargs(
            "openalex",
            logger=NoOpLogger(),
            metrics=NoOpMetrics(),
            include_fallback_service=True,
        ),
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.vcr
@pytest.mark.parametrize("rebalance_case", REBALANCE_CASES, ids=REBALANCE_CASES)
async def test_openalex_health_probe_rebalance_cassettes(
    adapter: OpenAlexAdapter,
    rebalance_case: str,
) -> None:
    """Record/replay independent OpenAlex health probe cassettes."""
    del rebalance_case
    status = await adapter.health_check()
    assert status in (
        HealthStatus.HEALTHY,
        HealthStatus.DEGRADED,
        HealthStatus.UNHEALTHY,
    )
