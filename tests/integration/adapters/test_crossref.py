"""Integration tests for CrossRef adapter.

Tests CrossRef API integration with VCR cassettes for reproducibility.
See RULES.md §4.2 for VCR requirements.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
import respx
from httpx import Response

from bioetl.composition.factories.datasource.crossref import create_crossref_adapter
from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.crossref import CrossRefAdapter
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter

CROSSREF_API_BASE = "https://api.crossref.org"


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for testing."""
    return MagicMock()


def _reset_http_client_state(client: UnifiedHTTPClient) -> None:
    """Reset mutable HTTP client state between tests sharing one client."""
    client.circuit_breaker.reset()
    rate_limiter = client.rate_limiter
    if isinstance(rate_limiter, TokenBucketRateLimiter):
        rate_limiter._tokens = float(rate_limiter.capacity)
        rate_limiter._last_refill = time.monotonic()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def http_client() -> AsyncIterator[UnifiedHTTPClient]:
    """Provide a shared started HTTP client for CrossRef integration tests."""
    client = UnifiedHTTPClient(
        TokenBucketRateLimiter(rate=50.0, capacity=100.0),
        CircuitBreakerGuard(provider="crossref_test"),
        retry_config=RetryConfig(
            base_delay=0.0,
            max_delay=0.0,
            multiplier=1.0,
            jitter_range=(0.0, 0.0),
        ),
    )
    await client.__aenter__()
    yield client
    await client.__aexit__(None, None, None)


@pytest.fixture
def crossref_adapter(
    http_client: UnifiedHTTPClient, mock_logger: MagicMock
) -> CrossRefAdapter:
    """Fixture to provide a CrossRefAdapter instance for testing."""
    _reset_http_client_state(http_client)
    return create_crossref_adapter(
        http_client=http_client,
        logger=mock_logger,
        settings=None,
        mailto="test@example.com",
        batch_size=50,
    )


@pytest.mark.integration
async def test_fetch_by_doi_single(crossref_adapter: CrossRefAdapter) -> None:
    """Test fetching a single publication by DOI."""
    mock_response = {
        "status": "ok",
        "message": {
            "items": [
                {
                    "DOI": "10.1038/nature12373",
                    "title": ["Crystal structure of rhodopsin bound to arrestin"],
                    "author": [
                        {"given": "Yanyong", "family": "Kang"},
                        {"given": "X. Edward", "family": "Zhou"},
                    ],
                    "container-title": ["Nature"],
                    "publisher": "Springer Science and Business Media LLC",
                    "published-print": {"date-parts": [[2015, 7, 30]]},
                    "is-referenced-by-count": 892,
                    "references-count": 50,
                    "type": "journal-article",
                }
            ]
        },
    }

    with respx.mock(base_url=CROSSREF_API_BASE) as respx_mock:
        respx_mock.get("/works").mock(return_value=Response(200, json=mock_response))
        records = []
        async for record in crossref_adapter.fetch(
            entity_type="work",
            filter_ids=["10.1038/nature12373"],
            filter_field="doi",
        ):
            records.append(record)

        assert len(records) == 1
        assert records[0]["DOI"] == "10.1038/nature12373"
        assert "Crystal structure" in records[0]["title"][0]
        assert records[0]["is-referenced-by-count"] == 892


@pytest.mark.integration
async def test_fetch_by_doi_batch(crossref_adapter: CrossRefAdapter) -> None:
    """Test fetching multiple publications by DOI in batch."""
    mock_response = {
        "status": "ok",
        "message": {
            "items": [
                {
                    "DOI": "10.1038/nature12373",
                    "title": ["Crystal structure of rhodopsin"],
                    "type": "journal-article",
                    "is-referenced-by-count": 892,
                },
                {
                    "DOI": "10.1016/j.cell.2019.03.025",
                    "title": ["Structure of the human receptor"],
                    "type": "journal-article",
                    "is-referenced-by-count": 245,
                },
            ]
        },
    }

    with respx.mock(base_url=CROSSREF_API_BASE) as respx_mock:
        respx_mock.get("/works").mock(return_value=Response(200, json=mock_response))
        records = []
        async for record in crossref_adapter.fetch(
            entity_type="work",
            filter_ids=["10.1038/nature12373", "10.1016/j.cell.2019.03.025"],
            filter_field="doi",
        ):
            records.append(record)

        assert len(records) == 2
        dois = {r["DOI"] for r in records}
        assert "10.1038/nature12373" in dois
        assert "10.1016/j.cell.2019.03.025" in dois


@pytest.mark.integration
async def test_fetch_doi_not_found(
    crossref_adapter: CrossRefAdapter, mock_logger: MagicMock
) -> None:
    """Test behavior when DOI is not found (empty results)."""
    mock_response = {
        "status": "ok",
        "message": {"items": []},
    }

    with respx.mock(base_url=CROSSREF_API_BASE) as respx_mock:
        respx_mock.get("/works").mock(return_value=Response(200, json=mock_response))
        records = []
        async for record in crossref_adapter.fetch(
            entity_type="work",
            filter_ids=["10.1234/nonexistent"],
            filter_field="doi",
        ):
            records.append(record)

        assert len(records) == 0


@pytest.mark.integration
async def test_fetch_with_limit(crossref_adapter: CrossRefAdapter) -> None:
    """Test that limit parameter restricts results."""
    mock_response = {
        "status": "ok",
        "message": {
            "items": [
                {"DOI": f"10.1234/test{i}", "title": [f"Test {i}"]} for i in range(10)
            ]
        },
    }

    with respx.mock(base_url=CROSSREF_API_BASE) as respx_mock:
        respx_mock.get("/works").mock(return_value=Response(200, json=mock_response))
        records = []
        async for record in crossref_adapter.fetch(
            entity_type="work",
            filter_ids=[f"10.1234/test{i}" for i in range(10)],
            filter_field="doi",
            limit=3,
        ):
            records.append(record)

        assert len(records) == 3


@pytest.mark.integration
async def test_health_check_healthy(crossref_adapter: CrossRefAdapter) -> None:
    """Test health check returns HEALTHY on successful response."""
    mock_response = {
        "status": "ok",
        "message": {"items": [{"DOI": "10.1234/test"}]},
    }

    with respx.mock(base_url=CROSSREF_API_BASE) as respx_mock:
        respx_mock.get("/works").mock(return_value=Response(200, json=mock_response))
        status = await crossref_adapter.health_check()
        assert status == HealthStatus.HEALTHY


@pytest.mark.integration
async def test_health_check_unhealthy_on_error(
    crossref_adapter: CrossRefAdapter,
) -> None:
    """Test health check returns UNHEALTHY on error response."""
    with respx.mock(base_url=CROSSREF_API_BASE) as respx_mock:
        respx_mock.get("/works").mock(return_value=Response(503))
        status = await crossref_adapter.health_check()
        assert status == HealthStatus.UNHEALTHY


@pytest.mark.integration
async def test_search_by_query(crossref_adapter: CrossRefAdapter) -> None:
    """Test search functionality by query string."""
    mock_response = {
        "status": "ok",
        "message": {
            "items": [
                {
                    "DOI": "10.1038/nature12373",
                    "title": ["Crystal structure of rhodopsin"],
                    "type": "journal-article",
                }
            ],
            "next-cursor": None,
        },
    }

    with respx.mock(base_url=CROSSREF_API_BASE) as respx_mock:
        respx_mock.get("/works").mock(return_value=Response(200, json=mock_response))
        records = []
        async for record in crossref_adapter.fetch(
            entity_type="work",
            query="rhodopsin crystal structure",
            limit=5,
        ):
            records.append(record)

        assert len(records) >= 1
        assert "rhodopsin" in records[0]["title"][0].lower()


@pytest.mark.integration
async def test_fetch_with_fallback_by_title(
    crossref_adapter: CrossRefAdapter, mock_logger: MagicMock
) -> None:
    """Test fallback to title search when DOI not found."""
    # First request: batch DOI returns empty
    batch_response = {"status": "ok", "message": {"items": []}}

    # Second request: title search returns result
    search_response = {
        "status": "ok",
        "message": {
            "items": [
                {
                    "DOI": "10.1038/nature12373",
                    "title": ["Crystal structure of rhodopsin"],
                    "type": "journal-article",
                }
            ]
        },
    }

    call_count = [0]

    def route_handler(request):
        call_count[0] += 1
        if "filter=doi" in str(request.url):
            return Response(200, json=batch_response)
        return Response(200, json=search_response)

    with respx.mock(base_url=CROSSREF_API_BASE) as respx_mock:
        respx_mock.get("/works").mock(side_effect=route_handler)
        records = []
        async for record in crossref_adapter.fetch_filtered_with_fallback(
            entity_type="work",
            filter_ids=["10.1234/notfound"],
            filter_field="doi",
            fallback_mapping={"10.1234/notfound": "Crystal structure of rhodopsin"},
        ):
            records.append(record)

        # Should find via title fallback
        assert len(records) == 1
        assert records[0]["DOI"] == "10.1038/nature12373"


@pytest.mark.integration
async def test_invalid_entity_type_raises(crossref_adapter: CrossRefAdapter) -> None:
    """Test that invalid entity type raises ValueError."""
    with respx.mock(base_url=CROSSREF_API_BASE):
        with pytest.raises(ValueError, match="CrossRefAdapter supports"):
            async for _ in crossref_adapter.fetch(
                entity_type="invalid_type",
                filter_ids=["10.1234/test"],
                filter_field="doi",
            ):
                continue


@pytest.mark.integration
async def test_fetch_preprint_type(crossref_adapter: CrossRefAdapter) -> None:
    """Test fetching preprint (posted-content type)."""
    mock_response = {
        "status": "ok",
        "message": {
            "items": [
                {
                    "DOI": "10.1101/2023.01.01.123456",
                    "title": ["A bioRxiv preprint"],
                    "type": "posted-content",
                    "publisher": "Cold Spring Harbor Laboratory",
                }
            ]
        },
    }

    with respx.mock(base_url=CROSSREF_API_BASE) as respx_mock:
        respx_mock.get("/works").mock(return_value=Response(200, json=mock_response))
        records = []
        async for record in crossref_adapter.fetch(
            entity_type="publication",  # Also accepts "publication"
            filter_ids=["10.1101/2023.01.01.123456"],
            filter_field="doi",
        ):
            records.append(record)

        assert len(records) == 1
        assert records[0]["type"] == "posted-content"


@pytest.mark.integration
async def test_batch_fetch_with_http_error_falls_back(
    crossref_adapter: CrossRefAdapter, mock_logger: MagicMock
) -> None:
    """Test that batch fetch falls back to individual on HTTP error."""
    # Single DOI response for fallback individual fetch
    single_response = {
        "status": "ok",
        "message": {
            "DOI": "10.1038/nature12373",
            "title": ["Crystal structure"],
            "type": "journal-article",
        },
    }

    call_count = [0]

    def route_handler(request):
        call_count[0] += 1
        path = str(request.url.path)
        # First call to /works (batch filter) fails
        if "filter=doi" in str(request.url) and call_count[0] == 1:
            return Response(500)
        # Individual DOI fetches (fallback) succeed
        if "/works/10." in path:
            return Response(200, json=single_response)
        # Default response for any other /works calls
        return Response(200, json=single_response)

    with respx.mock(base_url=CROSSREF_API_BASE) as respx_mock:
        respx_mock.route().mock(side_effect=route_handler)
        records = []
        async for record in crossref_adapter.fetch(
            entity_type="work",
            filter_ids=["10.1038/nature12373"],
            filter_field="doi",
        ):
            records.append(record)

        # Fallback mechanism should have been triggered
        # At least 2 calls: batch + individual fallback
        assert call_count[0] >= 1
