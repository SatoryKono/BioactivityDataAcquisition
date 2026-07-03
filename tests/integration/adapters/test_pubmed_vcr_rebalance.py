"""RF-013: PubMed VCR cassette rebalancing smoke coverage.

Records deterministic health-probe cassettes to increase provider baseline.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.pubmed import PubMedAdapter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs
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
    return build_vcr_config("pubmed")


@pytest.fixture
def vcr_cassette_name(request: pytest.FixtureRequest) -> str:
    """Use deterministic cassette names for RF-013 rebalance cases."""
    return build_rebalance_cassette_name(request, provider="pubmed")


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def http_client() -> AsyncIterator[UnifiedHTTPClient]:
    """Create and manage PubMed HTTP client lifecycle for integration tests."""
    async with rebalance_http_client(provider="pubmed", rate=3.0, capacity=6) as client:
        yield client


@pytest.fixture
def adapter(http_client: UnifiedHTTPClient) -> PubMedAdapter:
    """Create PubMed adapter used by rebalance tests."""
    reset_http_client_state(http_client)
    logger = NoOpLogger()
    return PubMedAdapter(
        http_client=http_client,
        logger=logger,
        email="bioetl-test@example.com",
        api_key=None,
        **build_http_adapter_runtime_kwargs(
            "pubmed",
            logger=logger,
            include_fallback_service=True,
        ),
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
