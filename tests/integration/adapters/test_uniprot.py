"""Integration tests for UniProt adapter.

These tests use VCR.py to record/replay HTTP interactions.
To record new cassettes: pytest --vcr-record=new_episodes
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.mark.integration
class TestUniProtClientIntegration:
    """Integration tests for UniProtClient.

    Note: These tests require VCR cassettes to run in CI.
    Use --vcr-record=new_episodes to record new cassettes.
    """

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create a mock logger for testing."""
        return MagicMock()

    @pytest.fixture
    def uniprot_client_internal(self, token_bucket: Any, circuit_breaker: Any) -> Any:
        """Create UniProt HTTP client for testing."""
        from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

        return UnifiedHTTPClient(
            rate_limiter=token_bucket,
            circuit_breaker=circuit_breaker,
            timeout=30.0,
        )

    @pytest.fixture
    def uniprot_adapter(self, uniprot_client_internal: Any, mock_logger: MagicMock) -> Any:
        """Create UniProtClient instance."""
        from bioetl.infrastructure.adapters.uniprot.client import UniProtClient

        return UniProtClient(http_client=uniprot_client_internal, logger=mock_logger)

    def test_provider_name(self, uniprot_adapter: Any) -> None:
        """Adapter should have correct provider name."""
        assert uniprot_adapter.provider_name == "uniprot"

    @pytest.mark.vcr
    async def test_health_check(self, uniprot_client_internal: Any, mock_logger: MagicMock) -> None:
        """Test UniProt health check probe.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_health_check
        """
        from bioetl.domain.types import HealthStatus
        from bioetl.infrastructure.adapters.uniprot.client import UniProtClient

        async with uniprot_client_internal:
            adapter = UniProtClient(http_client=uniprot_client_internal, logger=mock_logger)
            status = await adapter.health_check()

            # Should return a valid health status
            assert status in [
                HealthStatus.HEALTHY,
                HealthStatus.DEGRADED,
                HealthStatus.UNHEALTHY,
            ]

    @pytest.mark.vcr
    async def test_fetch_proteins(self, uniprot_client_internal: Any, mock_logger: MagicMock) -> None:
        """Test fetching proteins from UniProt.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_fetch_proteins
        """
        from bioetl.infrastructure.adapters.uniprot.client import UniProtClient

        async with uniprot_client_internal:
            adapter = UniProtClient(http_client=uniprot_client_internal, logger=mock_logger)

            records = []
            async for record in adapter.fetch("protein", query="gene:MYC", limit=2):
                records.append(record)

            assert len(records) > 0
            for record in records:
                assert "primaryAccession" in record
