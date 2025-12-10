"""Tests for SchemaBootstrapService."""

from __future__ import annotations

from unittest.mock import MagicMock



class TestSchemaBootstrapService:
    """Tests for SchemaBootstrapService."""

    def test_ensure_registered_uses_provided_provider(self) -> None:
        """Test ensure_registered uses provided schema provider."""
        mock_provider = MagicMock(spec=SchemaProviderABC)
        service = create_schema_bootstrap_service(schema_provider=mock_provider)

        result = service.ensure_registered()

        assert result is mock_provider

    def test_ensure_registered_creates_default_registry_when_none(self) -> None:
        """Test ensure_registered creates default registry when no provider given."""
        service = create_schema_bootstrap_service()

        result = service.ensure_registered()

        assert result is not None
        # Should have schemas registered
        assert len(result.list_schemas()) > 0
        assert "activity" in result.list_schemas()

    def test_ensure_registered_is_idempotent(self) -> None:
        """Test ensure_registered returns same provider on multiple calls."""
        service = create_schema_bootstrap_service()

        first_call = service.ensure_registered()
        second_call = service.ensure_registered()

        assert first_call is second_call


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

