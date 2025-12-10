"""Tests for SchemaContractProviderImpl."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.services.schema_contract_provider import (
    SchemaContractProviderImpl,
)
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.domain.validation import SchemaProviderABC


class TestSchemaContractProviderImpl:
    """Tests for SchemaContractProviderImpl."""

    @pytest.fixture
    def mock_schema_provider(self) -> MagicMock:
        """Create a mock schema provider."""
        provider = MagicMock(spec=SchemaProviderABC)
        return provider

    @pytest.fixture
    def contract_provider(
        self, mock_schema_provider: MagicMock
    ) -> SchemaContractProviderImpl:
        """Create a SchemaContractProviderImpl with mock provider."""
        return SchemaContractProviderImpl(mock_schema_provider)

    def test_implements_abc(
        self, contract_provider: SchemaContractProviderImpl
    ) -> None:
        """Verify implementation conforms to ABC."""
        assert isinstance(contract_provider, SchemaContractProviderABC)

    def test_get_output_schema_name_returns_from_contract(
        self, contract_provider: SchemaContractProviderImpl
    ) -> None:
        """Test get_output_schema_name returns schema name from pipeline contract."""
        # Known pipeline with explicit contract
        schema_name = contract_provider.get_output_schema_name("chembl.activity")

        assert schema_name == "activity_output"

    def test_get_output_schema_name_uses_default_entity(
        self, contract_provider: SchemaContractProviderImpl
    ) -> None:
        """Test get_output_schema_name uses default_entity for unknown pipeline."""
        schema_name = contract_provider.get_output_schema_name(
            "unknown.pipeline",
            default_entity="custom_entity",
        )

        assert schema_name == "custom_entity"

    def test_get_output_schema_name_uses_pipeline_code_as_fallback(
        self, contract_provider: SchemaContractProviderImpl
    ) -> None:
        """Test get_output_schema_name uses pipeline_code when no default_entity."""
        schema_name = contract_provider.get_output_schema_name("unknown.pipeline")

        assert schema_name == "unknown.pipeline"

    def test_get_field_configs_returns_field_list(
        self,
        contract_provider: SchemaContractProviderImpl,
        mock_schema_provider: MagicMock,
    ) -> None:
        """Test get_field_configs returns field configuration list."""
        # Create a mock schema that build_field_configs_from_schema can process
        mock_schema = MagicMock()
        mock_schema.to_schema.return_value.columns = {
            "field1": MagicMock(dtype="int64", nullable=False, description="Field 1"),
            "field2": MagicMock(dtype="object", nullable=True, description="Field 2"),
        }
        mock_schema_provider.get_schema.return_value = mock_schema

        fields = contract_provider.get_field_configs("test_schema")

        mock_schema_provider.get_schema.assert_called_once_with("test_schema")
        assert len(fields) == 2
        assert all(isinstance(f, dict) for f in fields)
        field_names = [f["name"] for f in fields]
        assert "field1" in field_names
        assert "field2" in field_names

    def test_get_field_configs_raises_on_missing_schema(
        self,
        contract_provider: SchemaContractProviderImpl,
        mock_schema_provider: MagicMock,
    ) -> None:
        """Test get_field_configs raises ValueError for unregistered schema."""
        mock_schema_provider.get_schema.side_effect = ValueError(
            "Schema 'missing' not found"
        )

        with pytest.raises(ValueError, match="not found"):
            contract_provider.get_field_configs("missing")


class TestSchemaContractProviderIntegration:
    """Integration tests using real schema registry."""

    @pytest.fixture
    def real_contract_provider(self) -> SchemaContractProviderImpl:
        """Create provider with real schema registry."""
        from bioetl.domain.schemas.registry import create_default_schema_registry

        registry = create_default_schema_registry()
        return SchemaContractProviderImpl(registry)

    def test_get_field_configs_for_activity_schema(
        self, real_contract_provider: SchemaContractProviderImpl
    ) -> None:
        """Test field configs from real activity schema."""
        fields = real_contract_provider.get_field_configs("activity")

        assert len(fields) > 5
        field_names = [f["name"] for f in fields]
        assert "action_type" in field_names
        assert "acquisition_timestamp" in field_names

        # Verify field structure
        sample_field = next(f for f in fields if f["name"] == "action_type")
        assert "name" in sample_field
        assert "data_type" in sample_field
        assert "is_nullable" in sample_field
        assert "is_filterable" in sample_field
        assert "description" in sample_field

    def test_get_output_schema_name_for_known_pipeline(
        self, real_contract_provider: SchemaContractProviderImpl
    ) -> None:
        """Test output schema name for known pipeline contracts."""
        test_cases = [
            ("chembl.activity", "activity_output"),
            ("chembl.assay", "assay_output"),
            ("chembl.molecule", "molecule_output"),
            ("chembl.target", "target_output"),
            ("chembl.document", "document_output"),
        ]

        for pipeline_code, expected_schema in test_cases:
            schema_name = real_contract_provider.get_output_schema_name(pipeline_code)
            assert (
                schema_name == expected_schema
            ), f"Pipeline {pipeline_code} should return {expected_schema}"
