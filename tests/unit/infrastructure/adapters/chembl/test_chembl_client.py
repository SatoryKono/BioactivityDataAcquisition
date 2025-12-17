"""Unit tests for ChEMBL client adapter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.infrastructure.adapters.chembl.client import (
    CHEMBL_API_BASE,
    ENTITY_MAPPING,
    ENTITY_PLURAL,
    ChemblAdapter,
)


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.fixture
def chembl_adapter(mock_http_client):
    """Create a ChemblAdapter instance."""
    return ChemblAdapter(http_client=mock_http_client, batch_size=100)


@pytest.mark.unit
class TestChemblAdapterInit:
    """Tests for ChemblAdapter initialization."""

    def test_init_default_values(self, mock_http_client):
        """Test adapter initialization with defaults."""
        adapter = ChemblAdapter(http_client=mock_http_client)
        assert adapter.batch_size == 1000
        assert adapter.provider_name == "chembl"

    def test_init_custom_batch_size(self, mock_http_client):
        """Test adapter initialization with custom batch size."""
        adapter = ChemblAdapter(http_client=mock_http_client, batch_size=500)
        assert adapter.batch_size == 500


@pytest.mark.unit
class TestChemblAdapterResourceUrl:
    """Tests for URL construction."""

    def test_get_resource_url_valid_entity(self, chembl_adapter):
        """Test URL construction for valid entity types."""
        for entity_type, resource in ENTITY_MAPPING.items():
            url = chembl_adapter._get_resource_url(entity_type)
            assert url == f"{CHEMBL_API_BASE}/{resource}.json"

    def test_get_resource_url_invalid_entity(self, chembl_adapter):
        """Test URL construction raises for invalid entity type."""
        with pytest.raises(ValueError, match="Unknown entity type"):
            chembl_adapter._get_resource_url("invalid_entity")


@pytest.mark.unit
class TestChemblAdapterContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_aenter_aexit(self, chembl_adapter, mock_http_client):
        """Test async context manager enters and exits correctly."""
        async with chembl_adapter as adapter:
            assert adapter is chembl_adapter

        mock_http_client.__aenter__.assert_called_once()
        mock_http_client.__aexit__.assert_called_once()


@pytest.mark.unit
class TestChemblAdapterEntityMapping:
    """Tests for entity type mapping."""

    def test_entity_mapping_contains_expected_types(self):
        """Test ENTITY_MAPPING contains all expected types."""
        expected_types = [
            "activity",
            "assay",
            "compound",
            "target",
            "document",
            "cell_line",
            "tissue",
        ]
        for entity_type in expected_types:
            assert entity_type in ENTITY_MAPPING

    def test_entity_plural_contains_expected_types(self):
        """Test ENTITY_PLURAL contains all expected types."""
        expected_plurals = {
            "activity": "activities",
            "assay": "assays",
            "molecule": "molecules",
            "target": "targets",
        }
        for singular, plural in expected_plurals.items():
            assert ENTITY_PLURAL[singular] == plural


@pytest.mark.unit
class TestChemblAdapterHealth:
    """Tests for health status tracking."""

    def test_initial_health_status(self, chembl_adapter):
        """Test initial health status is healthy."""
        from bioetl.domain.types import HealthStatus

        assert chembl_adapter._cached_health == HealthStatus.HEALTHY

    def test_consecutive_errors_starts_at_zero(self, chembl_adapter):
        """Test consecutive errors counter starts at zero."""
        assert chembl_adapter._consecutive_errors == 0
