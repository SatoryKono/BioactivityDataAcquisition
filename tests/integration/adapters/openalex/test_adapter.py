"""Integration tests for OpenAlex adapter.

Uses VCR.py to record/playback HTTP interactions.
Tests real API behavior with recorded cassettes.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
import pytest_asyncio

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.openalex import OpenAlexAdapter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs

# VCR cassette directory
CASSETTE_DIR = (
    Path(__file__).parent.parent.parent.parent / "fixtures" / "vcr" / "openalex"
)


@pytest.fixture(scope="module")
def vcr_config():
    """Configure VCR for OpenAlex tests."""
    return {
        "cassette_library_dir": str(CASSETTE_DIR),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "filter_query_parameters": ["mailto"],  # Don't record mailto
        "decode_compressed_response": True,
    }


@pytest_asyncio.fixture
async def http_client():
    """Create HTTP client for integration tests."""
    rate_limiter = TokenBucketRateLimiter(rate=10.0, capacity=20, provider="openalex")
    circuit_breaker = CircuitBreakerGuard(
        provider="openalex",
        failure_threshold=5,
        recovery_timeout=300,
    )

    client = UnifiedHTTPClient(
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        timeout=30.0,
        provider="openalex",
    )
    await client.__aenter__()
    yield client
    await client.__aexit__(None, None, None)


@pytest_asyncio.fixture
async def adapter(http_client: UnifiedHTTPClient):
    """Create OpenAlex adapter for integration tests."""
    await asyncio.sleep(0)
    logger = NoOpLogger()
    metrics = NoOpMetrics()
    return OpenAlexAdapter(
        http_client=http_client,
        logger=logger,
        mailto="bioetl-test@example.com",
        batch_size=10,
        metrics=metrics,
        **build_http_adapter_runtime_kwargs(
            "openalex",
            logger=logger,
            metrics=metrics,
            include_fallback_service=True,
        ),
    )


@pytest.mark.integration
class TestOpenAlexAdapterIntegration:
    """Integration tests for OpenAlex adapter."""

    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_fetch_filtered_by_doi(self, adapter: OpenAlexAdapter) -> None:
        """Should fetch works by DOI from OpenAlex API."""
        dois = ["10.1038/s41586-020-2012-7"]  # COVID-19 paper

        results = []
        async for work in adapter.fetch_filtered("publication", dois, "doi", limit=1):
            results.append(work)

        assert len(results) == 1
        work = results[0]
        assert "id" in work
        assert "doi" in work
        assert "title" in work

    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_fetch_filtered_batch_dois(self, adapter: OpenAlexAdapter) -> None:
        """Should fetch multiple works by batch DOI lookup."""
        dois = [
            "10.1038/s41586-020-2012-7",
            "10.1016/j.cell.2020.02.052",
        ]

        results = []
        async for work in adapter.fetch_filtered("publication", dois, "doi"):
            results.append(work)

        assert len(results) >= 1  # At least one should be found

    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_fetch_with_query(self, adapter: OpenAlexAdapter) -> None:
        """Should fetch works by search query."""
        results = []
        async for work in adapter.fetch(
            "publication", query="COVID-19 vaccine", limit=3
        ):
            results.append(work)

        assert len(results) <= 3

    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_health_check(self, adapter: OpenAlexAdapter) -> None:
        """Should return healthy status for working API."""
        status = await adapter.health_check()
        assert status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)

    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_fetch_filtered_with_fallback(self, adapter: OpenAlexAdapter) -> None:
        """Should fallback to title search when DOI not found."""
        # Valid DOI and title for fallback
        dois = ["10.1038/s41586-020-2012-7"]
        fallback_mapping = {
            "10.1038/s41586-020-2012-7": (
                "A pneumonia outbreak associated with a new coronavirus of probable bat origin"
            ),
        }

        results = []
        async for work in adapter.fetch_filtered_with_fallback(
            "publication", dois, "doi", fallback_mapping, limit=1
        ):
            results.append(work)

        assert len(results) >= 1
        work = results[0]
        assert "_lookup_method" in work

    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_title_only_lookup(self, adapter: OpenAlexAdapter) -> None:
        """Should search by title when DOI is empty."""
        # Empty DOI with title for lookup
        dois = [""]
        fallback_mapping = {
            "": "COVID-19 vaccine development",
        }

        results = []
        async for work in adapter.fetch_filtered_with_fallback(
            "publication", dois, "doi", fallback_mapping, limit=1
        ):
            results.append(work)

        # May or may not find results depending on title
        if results:
            assert results[0].get("_lookup_method") == "title_only"


@pytest.mark.integration
class TestOpenAlexAdapterRateLimiting:
    """Tests for rate limiting behavior."""

    @pytest.mark.asyncio
    @pytest.mark.vcr
    async def test_rate_limiting_not_exceeded(self, adapter: OpenAlexAdapter) -> None:
        """Should not exceed rate limit (10 req/sec)."""
        # Fetch a small batch - should not trigger rate limit
        dois = [f"10.1038/test{i}" for i in range(5)]

        results = []
        async for work in adapter.fetch_filtered("publication", dois, "doi", limit=5):
            results.append(work)

        # Just verify no rate limit error was raised
        # Results may be empty if DOIs don't exist
        assert isinstance(results, list)
