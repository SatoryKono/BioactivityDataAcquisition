"""Integration tests for UniProt adapter.

These tests use VCR.py to record/replay HTTP interactions.
To record new cassettes: pytest --vcr-record=new_episodes

Cassettes location: tests/fixtures/vcr/uniprot/
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs

# VCR cassette directory for UniProt adapter tests
CASSETTE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "vcr" / "uniprot"


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    """Configure VCR for UniProt adapter tests."""
    return {
        "cassette_library_dir": str(CASSETTE_DIR),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "decode_compressed_response": True,
    }


@pytest.mark.integration
class TestUniProtAdapterIntegration:
    """Integration tests for UniProtAdapter.

    Note: These tests require VCR cassettes to run in CI.
    Use --vcr-record=new_episodes to record new cassettes.
    """

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create a mock logger for testing."""
        return MagicMock()

    @pytest.fixture
    def uniprot_http_client(self, token_bucket: Any, circuit_breaker: Any) -> Any:
        """Create UniProt HTTP client for testing."""
        from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

        return UnifiedHTTPClient(
            rate_limiter=token_bucket,
            circuit_breaker=circuit_breaker,
            timeout=30.0,
        )

    @pytest.fixture
    def uniprot_adapter(self, uniprot_http_client: Any, mock_logger: MagicMock) -> Any:
        """Create UniProtAdapter instance."""
        from bioetl.infrastructure.adapters.uniprot import UniProtAdapter

        return UniProtAdapter(
            http_client=uniprot_http_client,
            logger=mock_logger,
            **build_http_adapter_runtime_kwargs(
                "uniprot",
                logger=mock_logger,
                include_fallback_service=True,
            ),
        )

    def test_uni_prot_adapter__provider_name__2ec88784(self, uniprot_adapter: Any) -> None:
        """Adapter should have correct provider name."""
        assert uniprot_adapter.provider_name == "uniprot"

    @pytest.mark.vcr
    async def test_uni_prot_adapter__health_check__8a60de40(
        self, uniprot_http_client: Any, mock_logger: MagicMock
    ) -> None:
        """Test UniProt health check probe.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_health_check
        """
        from bioetl.domain.types import HealthStatus
        from bioetl.infrastructure.adapters.uniprot import UniProtAdapter

        async with uniprot_http_client:
            adapter = UniProtAdapter(
                http_client=uniprot_http_client,
                logger=mock_logger,
                **build_http_adapter_runtime_kwargs(
                    "uniprot",
                    logger=mock_logger,
                    include_fallback_service=True,
                ),
            )
            status = await adapter.health_check()

            # Should return a valid health status
            assert status in [
                HealthStatus.HEALTHY,
                HealthStatus.DEGRADED,
                HealthStatus.UNHEALTHY,
            ]

    @pytest.mark.vcr
    async def test_fetch_proteins(
        self, uniprot_http_client: Any, mock_logger: MagicMock
    ) -> None:
        """Test fetching proteins from UniProt.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_fetch_proteins
        """
        from bioetl.infrastructure.adapters.uniprot import UniProtAdapter

        async with uniprot_http_client:
            adapter = UniProtAdapter(
                http_client=uniprot_http_client,
                logger=mock_logger,
                **build_http_adapter_runtime_kwargs(
                    "uniprot",
                    logger=mock_logger,
                    include_fallback_service=True,
                ),
            )

            records = []
            async for record in adapter.fetch("protein", query="gene:MYC", limit=2):
                records.append(record)

            assert len(records) > 0
            for record in records:
                assert "primaryAccession" in record
