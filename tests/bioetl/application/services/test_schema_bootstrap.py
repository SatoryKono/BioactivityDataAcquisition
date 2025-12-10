"""Tests for SchemaBootstrapService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.services.schema_bootstrap import (
    SchemaBootstrapService,
    create_schema_bootstrap_service,
)
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.domain.validation import SchemaProviderABC


class TestSchemaBootstrapService:
    """Tests for SchemaBootstrapService."""

    def test_ensure_registered_uses_provided_provider(self) -> None:
        """Test ensure_registered uses provided schema provider."""
        mock_provider = MagicMock(spec=SchemaProviderABC)
        service = SchemaBootstrapService(schema_provider=mock_provider)

        result = service.ensure_registered()

        assert result is mock_provider

    def test_ensure_registered_creates_default_registry_when_none(self) -> None:
        """Test ensure_registered creates default registry when no provider given."""
        service = SchemaBootstrapService()

        result = service.ensure_registered()

        assert result is not None
        # Should have schemas registered
        assert len(result.list_schemas()) > 0
        assert "activity" in result.list_schemas()

    def test_ensure_registered_is_idempotent(self) -> None:
        """Test ensure_registered returns same provider on multiple calls."""
        service = SchemaBootstrapService()

        first_call = service.ensure_registered()
        second_call = service.ensure_registered()

        assert first_call is second_call

    def test_create_contract_provider_returns_valid_implementation(self) -> None:
        """Test create_contract_provider returns SchemaContractProviderABC."""
        service = SchemaBootstrapService()

        provider = service.create_contract_provider()

        assert isinstance(provider, SchemaContractProviderABC)

    def test_create_contract_provider_uses_registered_schemas(self) -> None:
        """Test contract provider can access registered schemas."""
        service = SchemaBootstrapService()
        provider = service.create_contract_provider()

        # Should be able to get field configs for registered schema
        fields = provider.get_field_configs("activity")

        assert len(fields) > 0

    def test_create_contract_provider_with_custom_provider(self) -> None:
        """Test create_contract_provider works with custom provider."""
        from bioetl.domain.schemas.registry import create_default_schema_registry

        custom_registry = create_default_schema_registry()
        service = SchemaBootstrapService(schema_provider=custom_registry)

        provider = service.create_contract_provider()

        assert isinstance(provider, SchemaContractProviderABC)
        # Should work with custom provider
        schema_name = provider.get_output_schema_name("chembl.activity")
        assert schema_name == "activity_output"


class TestCreateSchemaBootstrapService:
    """Tests for create_schema_bootstrap_service factory function."""

    def test_creates_service_without_provider(self) -> None:
        """Test factory creates service without explicit provider."""
        service = create_schema_bootstrap_service()

        assert isinstance(service, SchemaBootstrapService)

    def test_creates_service_with_provider(self) -> None:
        """Test factory creates service with explicit provider."""
        mock_provider = MagicMock(spec=SchemaProviderABC)

        service = create_schema_bootstrap_service(schema_provider=mock_provider)

        assert isinstance(service, SchemaBootstrapService)
        assert service.ensure_registered() is mock_provider

    def test_created_service_works_end_to_end(self) -> None:
        """Test created service works for complete bootstrap flow."""
        service = create_schema_bootstrap_service()

        # Simulate bootstrap flow
        provider = service.ensure_registered()
        contract_provider = service.create_contract_provider()

        # Should be able to get schema info
        schema_name = contract_provider.get_output_schema_name(
            "chembl.activity",
            default_entity="activity",
        )
        fields = contract_provider.get_field_configs(schema_name)

        assert schema_name == "activity_output"
        assert len(fields) > 0
