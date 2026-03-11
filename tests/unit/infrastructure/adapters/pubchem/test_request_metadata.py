"""Unit tests for PubChem request-metadata behavior."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.pubchem import PubChemAdapter
from bioetl.infrastructure.adapters.pubchem.constants import PUBCHEM_API_BASE

pytestmark = pytest.mark.unit


@pytest.fixture
def adapter() -> PubChemAdapter:
    """Create a lightweight adapter instance for request-metadata tests."""
    pool = ThreadPoolExecutor(max_workers=1)
    adapter = PubChemAdapter(
        logger=MagicMock(),
        rate_limiter=TokenBucketRateLimiter(rate=5.0, capacity=10),
        circuit_breaker=CircuitBreakerGuard(provider="pubchem_test"),
        thread_pool=pool,
    )
    try:
        yield adapter
    finally:
        pool.shutdown(wait=False)


def test_get_source_metadata_returns_collector_state_and_clears_requests(
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


def test_clear_request_collector_resets_request_count(adapter: PubChemAdapter) -> None:
    """Clearing the collector should drop accumulated request state."""
    adapter._request_collector.record_request(
        url=f"{PUBCHEM_API_BASE}/compound/cid/2244/JSON",
        duration_ms=11.0,
        status_code=200,
    )

    assert adapter.request_count == 1

    adapter.clear_request_collector()

    assert adapter.request_count == 0
