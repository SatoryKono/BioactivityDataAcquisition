"""Integration tests for UniProt ID Mapping adapter.

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

# VCR cassette directory for UniProt adapter tests (shared with test_uniprot.py)
CASSETTE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "vcr" / "uniprot"


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    """Configure VCR for UniProt ID Mapping adapter tests."""
    return {
        "cassette_library_dir": str(CASSETTE_DIR),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "decode_compressed_response": True,
    }


@pytest.mark.integration
class TestUniProtIDMappingIntegration:
    """Integration tests for UniProtIDMappingClient.

    Note: These tests require VCR cassettes to run in CI.
    Use --vcr-record=new_episodes to record new cassettes.
    """

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create a mock logger for testing."""
        logger = MagicMock()
        logger.info = MagicMock()
        logger.debug = MagicMock()
        logger.warning = MagicMock()
        logger.error = MagicMock()
        return logger

    @pytest.fixture
    def uniprot_http_client(self, token_bucket: Any, circuit_breaker: Any) -> Any:
        """Create UniProt HTTP client for testing."""
        from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

        return UnifiedHTTPClient(
            rate_limiter=token_bucket,
            circuit_breaker=circuit_breaker,
            timeout=60.0,  # Longer timeout for ID mapping jobs
        )

    @pytest.fixture
    def idmapping_client(self, uniprot_http_client: Any, mock_logger: MagicMock) -> Any:
        """Create UniProtIDMappingClient instance."""
        from bioetl.infrastructure.adapters.uniprot.idmapping_client import (
            UniProtIDMappingClient,
        )

        return UniProtIDMappingClient(
            http_client=uniprot_http_client,
            logger=mock_logger,
        )

    def test_uni_prot_i_d_mapping__provider_name__11bdae69(
        self, idmapping_client: Any
    ) -> None:
        """Adapter should have correct provider name."""
        assert idmapping_client.provider_name == "uniprot_idmapping"

    @pytest.mark.vcr
    async def test_uni_prot_i_d_mapping__health_check__62c365d6(
        self, uniprot_http_client: Any, mock_logger: MagicMock
    ) -> None:
        """Test UniProt ID Mapping health check probe.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_health_check
        """
        from bioetl.domain.types import HealthStatus
        from bioetl.infrastructure.adapters.uniprot.idmapping_client import (
            UniProtIDMappingClient,
        )

        async with uniprot_http_client:
            client = UniProtIDMappingClient(
                http_client=uniprot_http_client,
                logger=mock_logger,
            )
            status = await client.health_check()

            # Should return a valid health status
            assert status in [
                HealthStatus.HEALTHY,
                HealthStatus.DEGRADED,
                HealthStatus.UNHEALTHY,
            ]

    @pytest.mark.vcr
    async def test_map_single_id(
        self, uniprot_http_client: Any, mock_logger: MagicMock
    ) -> None:
        """Test mapping a single ChEMBL ID.

        This test requires a VCR cassette.
        Record with: VCR_RECORD_MODE=new_episodes pytest -k test_map_single_id

        Note: CHEMBL204 corresponds to Factor X (UniProt: P00742).
        """
        from bioetl.infrastructure.adapters.uniprot.idmapping_client import (
            UniProtIDMappingClient,
        )

        async with uniprot_http_client:
            client = UniProtIDMappingClient(
                http_client=uniprot_http_client,
                logger=mock_logger,
            )

            result = await client.map_ids("ChEMBL", "UniProtKB", ["CHEMBL204"])

            assert "CHEMBL204" in result
            # P00742 is Factor X (Coagulation factor X)
            assert result["CHEMBL204"] is not None

    @pytest.mark.vcr
    async def test_map_multiple_ids(
        self, uniprot_http_client: Any, mock_logger: MagicMock
    ) -> None:
        """Test mapping multiple ChEMBL IDs.

        This test requires a VCR cassette.
        Record with: VCR_RECORD_MODE=new_episodes pytest -k test_map_multiple_ids
        """
        from bioetl.infrastructure.adapters.uniprot.idmapping_client import (
            UniProtIDMappingClient,
        )

        async with uniprot_http_client:
            client = UniProtIDMappingClient(
                http_client=uniprot_http_client,
                logger=mock_logger,
            )

            result = await client.map_ids(
                "ChEMBL",
                "UniProtKB",
                ["CHEMBL204", "CHEMBL205", "CHEMBL206"],
            )

            assert len(result) == 3
            # At least one should be found
            found_count = sum(1 for v in result.values() if v is not None)
            assert found_count > 0

    @pytest.mark.vcr
    async def test_map_not_found_id(
        self, uniprot_http_client: Any, mock_logger: MagicMock
    ) -> None:
        """Test mapping ID that doesn't exist.

        This test requires a VCR cassette.
        Record with: VCR_RECORD_MODE=new_episodes pytest -k test_map_not_found_id
        """
        from bioetl.infrastructure.adapters.uniprot.idmapping_client import (
            UniProtIDMappingClient,
        )

        async with uniprot_http_client:
            client = UniProtIDMappingClient(
                http_client=uniprot_http_client,
                logger=mock_logger,
            )

            result = await client.map_ids(
                "ChEMBL",
                "UniProtKB",
                ["CHEMBL99999999999"],
            )

            assert "CHEMBL99999999999" in result
            assert result["CHEMBL99999999999"] is None

    @pytest.mark.vcr
    async def test_map_empty_list(
        self, uniprot_http_client: Any, mock_logger: MagicMock
    ) -> None:
        """Test mapping empty list returns empty dict.

        No VCR cassette needed - no API call is made.
        """
        from bioetl.infrastructure.adapters.uniprot.idmapping_client import (
            UniProtIDMappingClient,
        )

        async with uniprot_http_client:
            client = UniProtIDMappingClient(
                http_client=uniprot_http_client,
                logger=mock_logger,
            )

            result = await client.map_ids("ChEMBL", "UniProtKB", [])

            assert result == {}

    @pytest.mark.vcr
    async def test_map_mixed_results(
        self, uniprot_http_client: Any, mock_logger: MagicMock
    ) -> None:
        """Test mapping with mixed results (some found, some not).

        This test requires a VCR cassette.
        Record with: VCR_RECORD_MODE=new_episodes pytest -k test_map_mixed_results
        """
        from bioetl.infrastructure.adapters.uniprot.idmapping_client import (
            UniProtIDMappingClient,
        )

        async with uniprot_http_client:
            client = UniProtIDMappingClient(
                http_client=uniprot_http_client,
                logger=mock_logger,
            )

            # Mix of known valid IDs and likely invalid ones
            result = await client.map_ids(
                "ChEMBL",
                "UniProtKB",
                ["CHEMBL204", "CHEMBL_INVALID_XYZ"],
            )

            assert len(result) == 2
            # CHEMBL204 should be found
            assert result["CHEMBL204"] is not None
            # Invalid should not be found
            assert result["CHEMBL_INVALID_XYZ"] is None
