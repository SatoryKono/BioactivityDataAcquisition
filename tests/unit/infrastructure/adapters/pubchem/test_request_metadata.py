"""Unit tests for PubChem request-metadata behavior."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.common.adapter_defaults import (
    create_default_error_handler,
)
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.pubchem import PubChemAdapter
from bioetl.infrastructure.adapters.pubchem.constants import PUBCHEM_API_BASE
from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper
from bioetl.infrastructure.adapters.pubchem.fetch_strategies import (
    PubChemFetchStrategies,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def adapter() -> PubChemAdapter:
    """Create a lightweight adapter instance for request-metadata tests."""
    pool = ThreadPoolExecutor(max_workers=1)
    logger = MagicMock()
    rate_limiter = TokenBucketRateLimiter(rate=5.0, capacity=10)
    circuit_breaker = CircuitBreakerGuard(provider="pubchem_test")
    request_collector = APIRequestCollector()
    entity_mapper = PubChemEntityMapper()

    async def run_in_executor(func, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(pool, func, *args)

    adapter = PubChemAdapter(
        logger=logger,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        thread_pool=pool,
        error_handler=create_default_error_handler(logger=logger, metrics=None),
        request_collector=request_collector,
        entity_mapper=entity_mapper,
        fetch_strategies=PubChemFetchStrategies(
            logger=logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            mapper=entity_mapper,
            run_in_executor=run_in_executor,
            provider_name=PubChemAdapter.provider_name,
            request_collector=request_collector,
        ),
    )
    try:
        yield adapter
    finally:
        pool.shutdown(wait=False)


def test_request_metadata__and_clears_requests__dc74bc77(
    adapter: PubChemAdapter,
) -> None:
    """Metadata snapshot should reflect collector state and consume it."""
    adapter._request_collector.record_request(
        url=f"{PUBCHEM_API_BASE}/compound/name/aspirin/JSON",
        duration_ms=20.0,
        status_code=200,
    )

    assert adapter.request_count == 1

    metadata = adapter.get_source_metadata(api_version="v1")

    assert metadata.url == PUBCHEM_API_BASE
    assert metadata.api_version == "v1"
    assert metadata.total_requests == 1
    assert adapter.request_count == 0


def test_request_metadata__resets_request_count__e4fdbe1a(adapter: PubChemAdapter) -> None:
    """Clearing the collector should drop accumulated request state."""
    adapter._request_collector.record_request(
        url=f"{PUBCHEM_API_BASE}/compound/cid/2244/JSON",
        duration_ms=11.0,
        status_code=200,
    )

    assert adapter.request_count == 1

    adapter.clear_request_collector()

    assert adapter.request_count == 0
