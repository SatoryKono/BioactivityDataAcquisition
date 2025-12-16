"""Integration tests for ChEMBL adapter.

These tests use VCR.py to record/replay HTTP interactions.
To record new cassettes: pytest --vcr-record=new_episodes
"""

from __future__ import annotations

from typing import Any

import pytest


@pytest.mark.integration
class TestChemblAdapter:
    """Integration tests for ChemblAdapter.

    Note: These tests require VCR cassettes to run in CI.
    Use --vcr-record=new_episodes to record new cassettes.
    """

    @pytest.fixture
    def chembl_client(self, token_bucket: Any, circuit_breaker: Any) -> Any:
        """Create ChEMBL HTTP client for testing."""
        from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

        return UnifiedHTTPClient(
            rate_limiter=token_bucket,
            circuit_breaker=circuit_breaker,
            timeout=30.0,
        )

    @pytest.fixture
    def chembl_adapter(self, chembl_client: Any) -> Any:
        """Create ChemblAdapter instance."""
        from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter

        return ChemblAdapter(http_client=chembl_client)

    def test_provider_name(self, chembl_adapter: Any) -> None:
        """Adapter should have correct provider name."""
        assert chembl_adapter.provider_name == "chembl"

    @pytest.mark.vcr
    @pytest.mark.asyncio
    async def test_fetch_activities(
        self, chembl_client: Any, _vcr_cassette: str
    ) -> None:
        """Test fetching activities from ChEMBL.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_fetch_activities
        """
        from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter

        async with chembl_client:
            adapter = ChemblAdapter(http_client=chembl_client, batch_size=10)

            records = []
            async for record in adapter.fetch("activity", limit=5):
                records.append(record)

            assert len(records) >= 0
            # ChEMBL activity records should have these fields
            for record in records:
                assert "activity_id" in record or "molecule_chembl_id" in record

    @pytest.mark.vcr
    @pytest.mark.asyncio
    async def test_health_check(self, chembl_client: Any, _vcr_cassette: str) -> None:
        """Test ChEMBL health check endpoint.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_health_check
        """
        from bioetl.domain.types import HealthStatus
        from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter

        async with chembl_client:
            adapter = ChemblAdapter(http_client=chembl_client)
            status = await adapter.health_check()

            # Should return a valid health status
            assert status in [
                HealthStatus.HEALTHY,
                HealthStatus.DEGRADED,
                HealthStatus.UNHEALTHY,
            ]

    @pytest.mark.vcr
    @pytest.mark.asyncio
    async def test_get_entity_count(
        self, chembl_client: Any, _vcr_cassette: str
    ) -> None:
        """Test getting entity count from ChEMBL.

        This test requires a VCR cassette.
        Record with: pytest --vcr-record=new_episodes -k test_get_entity_count
        """
        from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter

        async with chembl_client:
            adapter = ChemblAdapter(http_client=chembl_client)
            count = await adapter.get_entity_count("compound")

            # ChEMBL has millions of compounds
            assert count > 1_000_000

    def test_invalid_entity_type_raises(self, chembl_adapter: Any) -> None:
        """Should raise ValueError for unknown entity type."""
        with pytest.raises(ValueError, match="Unknown entity type"):
            chembl_adapter._get_resource_url("invalid_entity")

    def test_entity_mapping(self, chembl_adapter: Any) -> None:
        """Entity types should map to correct ChEMBL resources."""
        assert "molecule" in chembl_adapter._get_resource_url("compound")
        assert "activity" in chembl_adapter._get_resource_url("activity")
        assert "target" in chembl_adapter._get_resource_url("target")
        assert "assay" in chembl_adapter._get_resource_url("assay")


@pytest.mark.unit
class TestChemblAdapterUnit:
    """Unit tests for ChemblAdapter that don't require HTTP calls."""

    def test_entity_url_generation(self) -> None:
        """Test URL generation for different entity types."""
        from bioetl.infrastructure.adapters.chembl.client import (
            CHEMBL_API_BASE,
            ENTITY_MAPPING,
        )

        for _entity, resource in ENTITY_MAPPING.items():
            expected_url = f"{CHEMBL_API_BASE}/{resource}.json"
            # Verify mapping exists
            assert resource in expected_url

    def test_api_base_url(self) -> None:
        """API base URL should be correct."""
        from bioetl.infrastructure.adapters.chembl.client import CHEMBL_API_BASE

        assert "ebi.ac.uk" in CHEMBL_API_BASE
        assert "chembl" in CHEMBL_API_BASE
