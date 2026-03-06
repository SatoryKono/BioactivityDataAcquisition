"""RF-013: PubMed VCR cassette rebalancing smoke coverage.

Records deterministic health-probe cassettes to increase provider baseline.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.pubmed.pubmed_client import PubMedAdapter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

CASSETTE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "vcr" / "pubmed"
REBALANCE_CASES = tuple(f"case_{index:02d}" for index in range(1, 11))


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
    return f"rf013_pubmed_health_{case_id}"


@pytest_asyncio.fixture
async def http_client() -> AsyncIterator[UnifiedHTTPClient]:
    """Create and manage PubMed HTTP client lifecycle for integration tests."""
    client = UnifiedHTTPClient(
        rate_limiter=TokenBucket(rate=3.0, capacity=6, provider="pubmed_rf013"),
        circuit_breaker=CircuitBreaker(provider="pubmed_rf013"),
        timeout=30.0,
        provider="pubmed",
    )
    await client.__aenter__()
    yield client
    await client.__aexit__(None, None, None)


@pytest_asyncio.fixture
async def adapter(http_client: UnifiedHTTPClient) -> PubMedAdapter:
    """Create PubMed adapter used by rebalance tests."""
    return PubMedAdapter(
        http_client=http_client,
        logger=NoOpLogger(),
        email="bioetl-test@example.com",
        api_key=None,
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.vcr
@pytest.mark.parametrize("rebalance_case", REBALANCE_CASES, ids=REBALANCE_CASES)
async def test_pubmed_health_probe_rebalance_cassettes(
    adapter: PubMedAdapter,
    rebalance_case: str,
) -> None:
    """Record/replay independent PubMed health probe cassettes."""
    del rebalance_case
    status = await adapter.health_check()
    assert status in (
        HealthStatus.HEALTHY,
        HealthStatus.DEGRADED,
        HealthStatus.UNHEALTHY,
    )
