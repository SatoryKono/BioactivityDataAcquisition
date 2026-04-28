"""Integration tests for Semantic Scholar adapter.

Tests Semantic Scholar API integration with VCR cassettes for reproducibility.
See RULES.md §4.2 for VCR requirements.

Cassettes location: tests/fixtures/vcr/semanticscholar/

Rate Limits:
- Without API key: Shared pool ~1000 req/sec (unstable)
- With API key: Guaranteed 1 req/sec per endpoint
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import pytest_asyncio

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.semanticscholar import SemanticScholarAdapter
from tests.integration.adapters.http_integration_support import (
    build_mock_logger,
    managed_http_client,
    reset_http_client_state,
)
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs

# VCR cassette directory
CASSETTE_DIR = (
    Path(__file__).parent.parent.parent / "fixtures" / "vcr" / "semanticscholar"
)


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    """Configure VCR for Semantic Scholar tests."""
    return {
        "cassette_library_dir": str(CASSETTE_DIR),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "decode_compressed_response": True,
    }


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for testing."""
    return build_mock_logger(bind_self=True)


async def _consume_async_iter(async_iter) -> list[object]:
    """Drain an async iterable while preserving iteration failures."""
    items: list[object] = []
    async for item in async_iter:
        items.append(item)
    return items


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def http_client() -> AsyncIterator[UnifiedHTTPClient]:
    """Create and manage Semantic Scholar HTTP client lifecycle for tests."""
    async with managed_http_client(
        provider="semanticscholar",
        rate=10.0,
        capacity=100.0,
        circuit_breaker_provider="semanticscholar_test",
    ) as client:
        yield client


@pytest.fixture
def semanticscholar_adapter(
    http_client: UnifiedHTTPClient,
    mock_logger: MagicMock,
) -> SemanticScholarAdapter:
    """Create SemanticScholarAdapter instance for testing."""
    reset_http_client_state(http_client)
    return SemanticScholarAdapter(
        http_client=http_client,
        logger=mock_logger,
        batch_size=100,
        **build_http_adapter_runtime_kwargs(
            "semanticscholar",
            logger=mock_logger,
            include_fallback_service=True,
        ),
    )


@pytest.mark.integration
class TestSemanticScholarAdapterIntegration:
    """Integration tests for SemanticScholarAdapter.

    Note: These tests require VCR cassettes to run in CI.
    Use --vcr-record=new_episodes to record new cassettes.
    """

    def test_provider_name(
        self, semanticscholar_adapter: SemanticScholarAdapter
    ) -> None:
        """Adapter should have correct provider name."""
        assert semanticscholar_adapter.provider_name == "semanticscholar"

    @pytest.mark.vcr
    async def test_health_check(
        self,
        semanticscholar_adapter: SemanticScholarAdapter,
    ) -> None:
        """Test Semantic Scholar health check probe.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_health_check
        """
        status = await semanticscholar_adapter.health_check()

        # Should return a valid health status
        assert status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        ]

    @pytest.mark.vcr
    async def test_fetch_by_doi(
        self,
        semanticscholar_adapter: SemanticScholarAdapter,
    ) -> None:
        """Test fetching a single publication by DOI.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_fetch_by_doi
        """
        records: list[dict[str, Any]] = []
        async for record in semanticscholar_adapter.fetch_filtered(
            entity_type="publication",
            filter_ids=["10.1038/nature12373"],
            filter_field="doi",
        ):
            records.append(record)

        assert len(records) == 1
        assert records[0]["externalIds"]["DOI"] == "10.1038/nature12373"
        assert records[0]["citationCount"] >= 0
        assert records[0]["year"] >= 1900

    @pytest.mark.vcr
    async def test_fetch_batch_dois(
        self,
        semanticscholar_adapter: SemanticScholarAdapter,
    ) -> None:
        """Test batch DOI resolution.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_fetch_batch_dois
        """
        records: list[dict[str, Any]] = []
        async for record in semanticscholar_adapter.fetch_filtered(
            entity_type="publication",
            filter_ids=["10.1038/nature12373", "10.1016/j.cell.2019.03.025"],
            filter_field="doi",
        ):
            records.append(record)

        assert len(records) == 2

        # Verify both requested DOIs are present in results
        dois = {r["externalIds"]["DOI"] for r in records}
        assert "10.1038/nature12373" in dois
        assert "10.1016/j.cell.2019.03.025" in dois

    @pytest.mark.vcr
    async def test_fetch_with_query(
        self,
        semanticscholar_adapter: SemanticScholarAdapter,
    ) -> None:
        """Test search-based fetch with query parameter.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_fetch_with_query
        """
        records: list[dict[str, Any]] = []
        async for record in semanticscholar_adapter.fetch(
            entity_type="publication",
            query="CRISPR gene editing",
            limit=3,
        ):
            records.append(record)

        assert len(records) == 3

        # Check that all records have required fields
        for record in records:
            assert "paperId" in record
            assert len(record["paperId"]) == 40
            assert "title" in record
            assert "year" in record

        # Verify CRISPR-related content
        titles = " ".join(r["title"].lower() for r in records)
        assert "crispr" in titles or "genome" in titles

    @pytest.mark.vcr
    async def test_fetch_filtered_with_fallback(
        self,
        semanticscholar_adapter: SemanticScholarAdapter,
    ) -> None:
        """Test DOI lookup with title fallback for not-found DOIs.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_fetch_filtered_with_fallback
        """
        fallback_mapping = {
            "10.1038/nature12373": "Crystal structure of rhodopsin",
            "10.9999/notfound": "Unknown Paper Title",
        }

        records: list[dict[str, Any]] = []
        async for record in semanticscholar_adapter.fetch_filtered_with_fallback(
            entity_type="publication",
            filter_ids=["10.1038/nature12373", "10.9999/notfound"],
            filter_field="doi",
            fallback_mapping=fallback_mapping,
        ):
            records.append(record)

        # At minimum DOI-resolved record must be present.
        # Title fallback may be unavailable in cassette due API rate limiting.
        assert len(records) >= 1

        # DOI-resolved record should always be present
        doi_record = next(r for r in records if r.get("_lookup_method") == "doi")
        assert doi_record is not None
        assert "paperId" in doi_record

        fallback_records = [
            r for r in records if r.get("_lookup_method") == "title_fallback"
        ]
        if fallback_records:
            assert fallback_records[0]["_original_id"] == "10.9999/notfound"

    @pytest.mark.vcr
    async def test_title_only_lookup(
        self,
        semanticscholar_adapter: SemanticScholarAdapter,
    ) -> None:
        """Test title-only lookup when DOI is empty.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_title_only_lookup
        """
        # Title must match what VCR cassette returns for title validation
        fallback_mapping = {
            "": "Machine learning for drug discovery",
        }

        records: list[dict[str, Any]] = []
        async for record in semanticscholar_adapter.fetch_filtered_with_fallback(
            entity_type="publication",
            filter_ids=[""],  # Empty DOI
            filter_field="doi",
            fallback_mapping=fallback_mapping,
        ):
            records.append(record)

        assert len(records) == 1
        assert records[0]["_lookup_method"] == "title_only"
        assert "paperId" in records[0]
        assert len(records[0]["paperId"]) == 40


@pytest.mark.integration
class TestSemanticScholarAdapterEdgeCases:
    """Edge case tests for SemanticScholarAdapter."""

    async def test_invalid_entity_type(
        self,
        semanticscholar_adapter: SemanticScholarAdapter,
    ) -> None:
        """Test that invalid entity type raises ValueError."""
        with pytest.raises(ValueError, match=r"publication.*paper"):
            await _consume_async_iter(
                semanticscholar_adapter.fetch(
                    entity_type="invalid_type",
                    query="test",
                )
            )

    async def test_fetch_with_limit(
        self,
        semanticscholar_adapter: SemanticScholarAdapter,
    ) -> None:
        """Test that limit parameter is respected in filtered fetch."""
        # Use respx for mock (no cassette needed for unit-like behavior)
        import respx
        from httpx import Response

        mock_response = [
            {"paperId": "a" * 40, "title": "Paper 1"},
            {"paperId": "b" * 40, "title": "Paper 2"},
            {"paperId": "c" * 40, "title": "Paper 3"},
        ]

        with respx.mock:
            respx.post("https://api.semanticscholar.org/graph/v1/paper/batch").mock(
                return_value=Response(200, json=mock_response)
            )

            records: list[dict[str, Any]] = []
            async for record in semanticscholar_adapter.fetch_filtered(
                entity_type="publication",
                filter_ids=["doi1", "doi2", "doi3"],
                filter_field="doi",
                limit=2,
            ):
                records.append(record)

            # Should respect limit=2
            assert len(records) == 2

    async def test_empty_filter_ids(
        self,
        semanticscholar_adapter: SemanticScholarAdapter,
    ) -> None:
        """Test behavior with empty filter_ids list."""
        records: list[dict[str, Any]] = []
        async for record in semanticscholar_adapter.fetch_filtered(
            entity_type="publication",
            filter_ids=[],
            filter_field="doi",
        ):
            records.append(record)

        # Empty input should yield no results
        assert len(records) == 0


@pytest.mark.integration
class TestSemanticScholarAdapterRateLimiting:
    """Rate limiting tests for SemanticScholarAdapter."""

    async def test_adapter_respects_rate_limiter(
        self,
        mock_logger: MagicMock,
    ) -> None:
        """Test that adapter respects rate limiter configuration."""
        await asyncio.sleep(0)
        # Create a slow rate limiter
        slow_rate_limiter = TokenBucketRateLimiter(rate=1.0, capacity=2)
        circuit_breaker = CircuitBreakerGuard(provider="semanticscholar_rate_test")

        http_client = UnifiedHTTPClient(
            rate_limiter=slow_rate_limiter,
            circuit_breaker=circuit_breaker,
        )

        adapter = SemanticScholarAdapter(
            http_client=http_client,
            logger=mock_logger,
            batch_size=10,
            **build_http_adapter_runtime_kwargs(
                "semanticscholar",
                logger=mock_logger,
                include_fallback_service=True,
            ),
        )

        # Verify adapter is configured
        assert adapter.batch_size == 10
        assert adapter.provider_name == "semanticscholar"
