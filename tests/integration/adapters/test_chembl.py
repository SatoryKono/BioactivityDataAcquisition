# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Integration tests for ChEMBL adapter.

The adapter-level tests below use a deterministic replay HTTP seam so routine
runs do not depend on live ChEMBL latency. Broader ChEMBL pipeline tests keep
their VCR cassettes under tests/fixtures/vcr/chembl/.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import httpx

# VCR cassette directory for ChEMBL adapter tests
CASSETTE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "vcr" / "chembl"


class _ReplayChemblHTTPClient:
    """Fast deterministic ChEMBL HTTP seam for adapter integration tests."""

    def __init__(self, circuit_breaker: Any) -> None:
        self.circuit_breaker = circuit_breaker
        self.requests: list[tuple[str, dict[str, object]]] = []

    async def __aenter__(self) -> _ReplayChemblHTTPClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        del exc_type, exc_val, exc_tb

    async def get(
        self,
        url: str,
        params: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        del headers
        request_params = dict(params or {})
        self.requests.append((url, request_params))
        return self._response(url=url, params=request_params)

    async def get_once(
        self,
        url: str,
        params: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        return await self.get(url, params=params, headers=headers)

    def _response(self, *, url: str, params: dict[str, object]) -> httpx.Response:
        request = httpx.Request("GET", url, params=params)
        if url.endswith("/status"):
            return httpx.Response(200, json={"status": "UP"}, request=request)
        if url.endswith("/molecule"):
            return httpx.Response(
                200,
                json={"molecules": [], "page_meta": {"total_count": 2_426_731}},
                request=request,
            )
        if url.endswith("/activity"):
            expected_params = {"format": "json", "limit": 5, "offset": 0}
            assert params == expected_params
            return httpx.Response(
                200,
                json={
                    "activities": [
                        {"activity_id": 31863},
                        {"activity_id": 31864},
                        {"activity_id": 31865},
                        {"activity_id": 31866},
                        {"activity_id": 31867},
                    ],
                    "page_meta": {
                        "limit": 5,
                        "next": "/chembl/api/data/activity?limit=5&offset=5",
                        "offset": 0,
                        "previous": None,
                        "total_count": 24_267_312,
                    },
                },
                request=request,
            )
        return httpx.Response(404, json={"detail": "not found"}, request=request)


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    """Configure VCR for ChEMBL adapter tests."""
    return {
        "cassette_library_dir": str(CASSETTE_DIR),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "decode_compressed_response": True,
    }


@pytest.mark.integration
class TestChemblAdapter:
    """Integration tests for ChemblAdapter.

    Note: These tests require VCR cassettes to run in CI.
    Use --vcr-record=new_episodes to record new cassettes.
    """

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create a mock logger for testing."""
        return MagicMock()

    @pytest.fixture
    def chembl_client(self, token_bucket: Any, circuit_breaker: Any) -> Any:
        """Create deterministic ChEMBL replay client for adapter integration tests."""
        del token_bucket
        return _ReplayChemblHTTPClient(circuit_breaker)

    @pytest.fixture
    def chembl_adapter(self, chembl_client: Any, mock_logger: MagicMock) -> Any:
        """Create ChemblAdapter instance."""
        from bioetl.infrastructure.adapters.chembl import ChemblAdapter

        return ChemblAdapter(http_client=chembl_client, logger=mock_logger)

    def test_provider_name(self, chembl_adapter: Any) -> None:
        """Adapter should have correct provider name."""
        assert chembl_adapter.provider_name == "chembl"

    async def test_fetch_activities(
        self, chembl_client: Any, mock_logger: MagicMock
    ) -> None:
        """Test fetching activities from a replayed ChEMBL response."""
        from bioetl.domain.resilience import AdapterConfig
        from bioetl.infrastructure.adapters.chembl import ChemblAdapter

        async with chembl_client:
            adapter = ChemblAdapter(
                http_client=chembl_client,
                logger=mock_logger,
                adapter_config=AdapterConfig(page_size=10),
            )

            records = []
            async for record in adapter.fetch("activity", limit=5):
                records.append(record)

            assert len(records) > 0
            # ChEMBL activity records should have these fields
            for record in records:
                assert "activity_id" in record

    async def test_health_check(
        self, chembl_client: Any, mock_logger: MagicMock
    ) -> None:
        """Test ChEMBL health check response handling."""
        from bioetl.domain.types import HealthStatus
        from bioetl.infrastructure.adapters.chembl import ChemblAdapter

        async with chembl_client:
            adapter = ChemblAdapter(http_client=chembl_client, logger=mock_logger)
            status = await adapter.health_check()

            # Should return a valid health status
            assert status in [
                HealthStatus.HEALTHY,
                HealthStatus.DEGRADED,
                HealthStatus.UNHEALTHY,
            ]

    async def test_get_entity_count(
        self, chembl_client: Any, mock_logger: MagicMock
    ) -> None:
        """Test getting entity count from a replayed ChEMBL response."""
        from bioetl.infrastructure.adapters.chembl import ChemblAdapter

        async with chembl_client:
            adapter = ChemblAdapter(http_client=chembl_client, logger=mock_logger)
            count = await adapter.get_entity_count("compound")

            # ChEMBL has millions of compounds
            assert count > 1_000_000

    def test_invalid_entity_type_raises(self, chembl_adapter: Any) -> None:
        """Should raise ValueError for unknown entity type."""
        from bioetl.infrastructure.adapters.chembl.entity_mapper import (
            ChemblEntityMapper,
        )

        with pytest.raises(ValueError, match="Unknown entity type"):
            ChemblEntityMapper.get_resource_url("invalid_entity")

    def test_entity_mapping(self, chembl_adapter: Any) -> None:
        """Entity types should map to correct ChEMBL resources."""
        from bioetl.infrastructure.adapters.chembl.entity_mapper import (
            ChemblEntityMapper,
        )

        assert "molecule" in ChemblEntityMapper.get_resource_url("compound")
        assert "activity" in ChemblEntityMapper.get_resource_url("activity")
        assert "target" in ChemblEntityMapper.get_resource_url("target")
        assert "assay" in ChemblEntityMapper.get_resource_url("assay")


@pytest.mark.unit
class TestChemblAdapterUnit:
    """Unit tests for ChemblAdapter that don't require HTTP calls."""

    def test_entity_url_generation(self) -> None:
        """Test URL generation for different entity types."""
        from bioetl.infrastructure.adapters.chembl.entity_mapper import (
            CHEMBL_API_BASE,
            ENTITY_MAPPING,
        )

        for _entity, resource in ENTITY_MAPPING.items():
            expected_url = f"{CHEMBL_API_BASE}/{resource}.json"
            # Verify mapping exists
            assert resource in expected_url

    def test_api_base_url(self) -> None:
        """API base URL should be correct."""
        from bioetl.infrastructure.adapters.chembl.entity_mapper import CHEMBL_API_BASE

        assert "ebi.ac.uk" in CHEMBL_API_BASE
        assert "chembl" in CHEMBL_API_BASE
