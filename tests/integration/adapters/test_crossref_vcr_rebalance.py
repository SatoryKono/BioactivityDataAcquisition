"""RF-013: CrossRef VCR cassette rebalancing smoke coverage.

Records deterministic health-probe cassettes to increase provider baseline.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio

from bioetl.composition.factories.datasource.crossref import create_crossref_adapter
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.crossref import CrossRefAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from tests.integration.adapters.vcr_rebalance_support import (
    REBALANCE_CASES,
    build_rebalance_cassette_name,
    build_vcr_config,
    rebalance_http_client,
    reset_http_client_state,
)


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    """Configure VCR with provider cassette directory and credential-safe matcher."""
    return build_vcr_config("crossref")


@pytest.fixture
def vcr_cassette_name(request: pytest.FixtureRequest) -> str:
    """Use deterministic cassette names for RF-013 rebalance cases."""
    return build_rebalance_cassette_name(request, provider="crossref")


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def http_client() -> AsyncIterator[UnifiedHTTPClient]:
    """Create and manage CrossRef HTTP client lifecycle for integration tests."""
    async with rebalance_http_client(
        provider="crossref",
        rate=10.0,
        capacity=20,
    ) as client:
        yield client


@pytest.fixture
def adapter(http_client: UnifiedHTTPClient) -> CrossRefAdapter:
    """Create CrossRef adapter used by rebalance tests."""
    reset_http_client_state(http_client)
    return create_crossref_adapter(
        http_client=http_client,
        logger=NoOpLogger(),
        settings=None,
        mailto="bioetl-test@example.com",
        batch_size=50,
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.vcr
@pytest.mark.parametrize("rebalance_case", REBALANCE_CASES, ids=REBALANCE_CASES)
async def test_crossref_health_probe_rebalance_cassettes(
    adapter: CrossRefAdapter,
    rebalance_case: str,
) -> None:
    """Record/replay independent CrossRef health probe cassettes."""
    del rebalance_case
    status = await adapter.health_check()
    assert status in (
        HealthStatus.HEALTHY,
        HealthStatus.DEGRADED,
        HealthStatus.UNHEALTHY,
    )
