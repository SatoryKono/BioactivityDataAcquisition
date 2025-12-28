"""Integration tests for CrossRef adapter.

These tests use VCR.py to record/replay HTTP interactions.
To record new cassettes: pytest --vcr-record=new_episodes
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.mark.integration
class TestCrossRefAdapter:
    """Integration tests for CrossRefAdapter.

    Note: These tests require VCR cassettes to run in CI.
    Use --vcr-record=new_episodes to record new cassettes.
    """

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create a mock logger for testing."""
        return MagicMock()

    @pytest.fixture
    def crossref_client(self, token_bucket: Any, circuit_breaker: Any) -> Any:
        """Create CrossRef HTTP client for testing."""
        from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

        return UnifiedHTTPClient(
            rate_limiter=token_bucket,
            circuit_breaker=circuit_breaker,
            timeout=30.0,
        )

    @pytest.fixture
    def crossref_adapter(self, crossref_client: Any, mock_logger: MagicMock) -> Any:
        """Create CrossRefAdapter instance."""
        from bioetl.infrastructure.adapters.crossref.client import CrossRefAdapter

        return CrossRefAdapter(
            http_client=crossref_client,
            logger=mock_logger,
            mailto="test@example.com",
        )

    def test_provider_name(self, crossref_adapter: Any) -> None:
        """Adapter should have correct provider name."""
        assert crossref_adapter.provider_name == "crossref"

    @pytest.mark.vcr(cassette_library_dir="tests/fixtures/vcr/crossref")
    async def test_fetch_publications(
        self, crossref_client: Any, mock_logger: MagicMock
    ) -> None:
        """Test fetching publications from CrossRef.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_fetch_publications
        """
        from bioetl.infrastructure.adapters.crossref.client import CrossRefAdapter

        async with crossref_client:
            adapter = CrossRefAdapter(
                http_client=crossref_client,
                logger=mock_logger,
                batch_size=5,
                mailto="test@example.com",
            )

            records = []
            async for record in adapter.fetch("publication", limit=5):
                records.append(record)

            assert len(records) > 0
            # CrossRef records should have DOI
            for record in records:
                assert "DOI" in record
                assert record["DOI"].startswith("10.")

    @pytest.mark.vcr(cassette_library_dir="tests/fixtures/vcr/crossref")
    async def test_health_check(
        self, crossref_client: Any, mock_logger: MagicMock
    ) -> None:
        """Test CrossRef health check endpoint.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_health_check
        """
        from bioetl.domain.types import HealthStatus
        from bioetl.infrastructure.adapters.crossref.client import CrossRefAdapter

        async with crossref_client:
            adapter = CrossRefAdapter(
                http_client=crossref_client,
                logger=mock_logger,
                mailto="test@example.com",
            )
            status = await adapter.health_check()

            # Should return a valid health status
            assert status in [
                HealthStatus.HEALTHY,
                HealthStatus.DEGRADED,
                HealthStatus.UNHEALTHY,
            ]

    @pytest.mark.vcr(cassette_library_dir="tests/fixtures/vcr/crossref")
    async def test_get_entity_count(
        self, crossref_client: Any, mock_logger: MagicMock
    ) -> None:
        """Test getting entity count from CrossRef.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_get_entity_count
        """
        from bioetl.infrastructure.adapters.crossref.client import CrossRefAdapter

        async with crossref_client:
            adapter = CrossRefAdapter(
                http_client=crossref_client,
                logger=mock_logger,
                mailto="test@example.com",
            )
            count = await adapter.get_entity_count("publication")

            # CrossRef has millions of works
            assert count > 100_000_000

    def test_invalid_entity_type_raises(self, crossref_adapter: Any) -> None:
        """Should raise ValueError for unknown entity type."""
        import asyncio

        with pytest.raises(ValueError, match="only supports 'publication' or 'work'"):
            asyncio.get_event_loop().run_until_complete(
                crossref_adapter.fetch("invalid_entity").__anext__()
            )

    def test_doi_normalization(self, crossref_adapter: Any) -> None:
        """DOI normalization should handle various formats."""
        # Test lowercase
        assert crossref_adapter._normalize_doi("10.1234/ABC") == "10.1234/abc"

        # Test URL prefix removal
        assert (
            crossref_adapter._normalize_doi("https://doi.org/10.1234/test")
            == "10.1234/test"
        )
        assert (
            crossref_adapter._normalize_doi("http://dx.doi.org/10.1234/test")
            == "10.1234/test"
        )

        # Test whitespace stripping
        assert crossref_adapter._normalize_doi("  10.1234/test  ") == "10.1234/test"


@pytest.mark.unit
class TestCrossRefAdapterUnit:
    """Unit tests for CrossRefAdapter that don't require HTTP calls."""

    def test_api_constants(self) -> None:
        """API constants should be correct."""
        from bioetl.infrastructure.adapters.crossref.client import (
            CROSSREF_BASE_URL,
            CROSSREF_WORKS_URL,
        )

        assert CROSSREF_BASE_URL == "https://api.crossref.org"
        assert CROSSREF_WORKS_URL == "https://api.crossref.org/works"

    def test_health_aware_batch_size_healthy(self) -> None:
        """Healthy adapter should use normal batch size."""
        from unittest.mock import MagicMock

        from bioetl.domain.types import HealthStatus
        from bioetl.infrastructure.adapters.crossref.client import CrossRefAdapter

        mock_client = MagicMock()
        mock_logger = MagicMock()

        adapter = CrossRefAdapter(
            http_client=mock_client,
            logger=mock_logger,
            batch_size=100,
        )

        # Healthy by default
        assert adapter._cached_health == HealthStatus.HEALTHY
        assert adapter._get_effective_batch_size() == 100

    def test_health_aware_batch_size_degraded(self) -> None:
        """Degraded adapter should halve batch size."""
        from unittest.mock import MagicMock

        from bioetl.domain.types import HealthStatus
        from bioetl.infrastructure.adapters.crossref.client import CrossRefAdapter

        mock_client = MagicMock()
        mock_logger = MagicMock()

        adapter = CrossRefAdapter(
            http_client=mock_client,
            logger=mock_logger,
            batch_size=100,
        )

        # Simulate degraded state
        adapter._consecutive_errors = 1
        adapter._update_health()
        assert adapter._cached_health == HealthStatus.DEGRADED
        assert adapter._get_effective_batch_size() == 50  # Half of 100

    def test_health_aware_batch_size_unhealthy_raises(self) -> None:
        """Unhealthy adapter should raise CriticalError."""
        from unittest.mock import MagicMock

        import pytest

        from bioetl.domain.exceptions import CriticalError
        from bioetl.domain.types import HealthStatus
        from bioetl.infrastructure.adapters.crossref.client import CrossRefAdapter

        mock_client = MagicMock()
        mock_logger = MagicMock()

        adapter = CrossRefAdapter(
            http_client=mock_client,
            logger=mock_logger,
            batch_size=100,
        )

        # Simulate unhealthy state
        adapter._consecutive_errors = 3
        adapter._update_health()
        assert adapter._cached_health == HealthStatus.UNHEALTHY

        with pytest.raises(CriticalError, match="UNHEALTHY"):
            adapter._get_effective_batch_size()
