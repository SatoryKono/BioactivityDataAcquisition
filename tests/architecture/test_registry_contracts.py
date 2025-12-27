"""Tests for Registry pattern contracts.

Verifies that all registries follow the unified BaseRegistry protocol.
Implements CLAUDE.md §6.3.3 requirements.
"""

from __future__ import annotations

import typing

import pytest


class TestRegistryProtocol:
    """All registries must implement BaseRegistry protocol."""

    def test_pipeline_registry_has_required_methods(self) -> None:
        """PipelineRegistry must have get, register_factory, list_pipelines methods."""
        from bioetl.composition.registry import PipelineRegistry

        assert hasattr(PipelineRegistry, "get"), (
            "PipelineRegistry MUST have get() method"
        )
        assert hasattr(PipelineRegistry, "register_factory"), (
            "PipelineRegistry MUST have register_factory() method"
        )
        assert hasattr(PipelineRegistry, "list_pipelines"), (
            "PipelineRegistry MUST have list_pipelines() method"
        )

    def test_datasource_registry_has_required_methods(self) -> None:
        """DataSourceRegistry must have get, register, list_providers methods."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        assert hasattr(DataSourceRegistry, "get"), (
            "DataSourceRegistry MUST have get() method"
        )
        assert hasattr(DataSourceRegistry, "register"), (
            "DataSourceRegistry MUST have register() method"
        )
        assert hasattr(DataSourceRegistry, "list_providers"), (
            "DataSourceRegistry MUST have list_providers() method"
        )

    def test_provider_registry_has_required_methods(self) -> None:
        """ProviderRegistry must have get, register, list_providers methods."""
        from bioetl.composition.providers.provider_registry import ProviderRegistry

        assert hasattr(ProviderRegistry, "get"), (
            "ProviderRegistry MUST have get() method"
        )
        assert hasattr(ProviderRegistry, "register"), (
            "ProviderRegistry MUST have register() method"
        )
        assert hasattr(ProviderRegistry, "list_providers"), (
            "ProviderRegistry MUST have list_providers() method"
        )

    def test_provider_registry_has_create_adapter(self) -> None:
        """ProviderRegistry must have create_adapter for adapter instantiation."""
        from bioetl.composition.providers.provider_registry import ProviderRegistry

        assert hasattr(ProviderRegistry, "create_adapter"), (
            "ProviderRegistry MUST have create_adapter() method for DI"
        )


class TestRegistryRaiseOnMissingKey:
    """Registries must raise clear error for unknown keys."""

    def test_pipeline_registry_raises_on_missing(self) -> None:
        """PipelineRegistry raises RuntimeError or ValueError for unknown pipeline."""
        from bioetl.composition.registry import PipelineRegistry

        with pytest.raises((RuntimeError, ValueError, KeyError)):
            PipelineRegistry.get("nonexistent_pipeline_12345")

    def test_datasource_registry_raises_on_missing(self) -> None:
        """DataSourceRegistry raises KeyError for unknown provider."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        with pytest.raises(KeyError):
            DataSourceRegistry.get("nonexistent_provider_12345")

    def test_provider_registry_raises_on_missing(self) -> None:
        """ProviderRegistry raises KeyError for unknown provider."""
        from bioetl.composition.providers.provider_registry import ProviderRegistry

        with pytest.raises(KeyError):
            ProviderRegistry.get("nonexistent_provider_12345")


class TestRegistryClassVars:
    """Registries use ClassVar for storage (singleton pattern)."""

    def test_pipeline_registry_uses_classvar(self) -> None:
        """PipelineRegistry._registry must be ClassVar."""
        from bioetl.composition.registry import PipelineRegistry

        # ClassVar should be in annotations
        assert "_registry" in PipelineRegistry.__annotations__, (
            "PipelineRegistry MUST have _registry annotation"
        )

        # Check it's a ClassVar
        hint = PipelineRegistry.__annotations__["_registry"]
        # ClassVar is represented as typing.ClassVar[...]
        assert "ClassVar" in str(hint), (
            "PipelineRegistry._registry MUST be ClassVar for singleton pattern"
        )

    def test_datasource_registry_uses_classvar(self) -> None:
        """DataSourceRegistry._creators must be ClassVar."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        assert "_creators" in DataSourceRegistry.__annotations__, (
            "DataSourceRegistry MUST have _creators annotation"
        )

        hint = DataSourceRegistry.__annotations__["_creators"]
        assert "ClassVar" in str(hint), (
            "DataSourceRegistry._creators MUST be ClassVar for singleton pattern"
        )

    def test_provider_registry_uses_classvar(self) -> None:
        """ProviderRegistry._providers must be ClassVar."""
        from bioetl.composition.providers.provider_registry import ProviderRegistry

        assert "_providers" in ProviderRegistry.__annotations__, (
            "ProviderRegistry MUST have _providers annotation"
        )

        hint = ProviderRegistry.__annotations__["_providers"]
        assert "ClassVar" in str(hint), (
            "ProviderRegistry._providers MUST be ClassVar for singleton pattern"
        )


class TestRegistryReturnTypes:
    """Registries must return proper types."""

    def test_pipeline_registry_list_returns_list(self) -> None:
        """PipelineRegistry.list_pipelines must return list[str]."""
        from bioetl.composition.registry import PipelineRegistry

        result = PipelineRegistry.list_pipelines()
        assert isinstance(result, list), (
            "list_pipelines() MUST return a list"
        )
        # All items should be strings
        for item in result:
            assert isinstance(item, str), (
                "list_pipelines() MUST return list of strings"
            )

    def test_datasource_registry_list_returns_list(self) -> None:
        """DataSourceRegistry.list_providers must return list[str]."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        result = DataSourceRegistry.list_providers()
        assert isinstance(result, list), (
            "list_providers() MUST return a list"
        )
        for item in result:
            assert isinstance(item, str), (
                "list_providers() MUST return list of strings"
            )

    def test_provider_registry_list_returns_sorted_list(self) -> None:
        """ProviderRegistry.list_providers must return sorted list[str]."""
        from bioetl.composition.providers.provider_registry import ProviderRegistry

        result = ProviderRegistry.list_providers()
        assert isinstance(result, list), (
            "list_providers() MUST return a list"
        )
        # Check it's sorted
        assert result == sorted(result), (
            "list_providers() MUST return sorted list"
        )


class TestRegistryConsistency:
    """Test consistency between registries."""

    def test_datasource_includes_provider_registry_providers(self) -> None:
        """DataSourceRegistry.list_providers includes ProviderRegistry entries."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )
        from bioetl.composition.providers import ensure_providers_loaded

        # Ensure providers are loaded
        ensure_providers_loaded()

        providers = DataSourceRegistry.list_providers()

        # Should include common providers
        common_providers = {"chembl", "pubchem", "uniprot"}
        for provider in common_providers:
            assert provider in providers, (
                f"DataSourceRegistry MUST include {provider}"
            )


class TestRegistryFactoryProtocol:
    """Test that PipelineRegistry has proper factory protocol."""

    def test_pipeline_factory_protocol_is_runtime_checkable(self) -> None:
        """PipelineFactoryProtocol must be @runtime_checkable."""
        from bioetl.composition.registry import PipelineFactoryProtocol

        # Test by attempting isinstance() - non-runtime_checkable raises TypeError
        class DummyImpl:
            """Dummy class for testing isinstance()."""
            pass

        try:
            isinstance(DummyImpl(), PipelineFactoryProtocol)
            is_runtime_checkable = True
        except TypeError:
            is_runtime_checkable = False

        assert is_runtime_checkable, (
            "PipelineFactoryProtocol MUST be @runtime_checkable"
        )

    def test_pipeline_factory_protocol_has_required_attributes(self) -> None:
        """PipelineFactoryProtocol must define pipeline_name and silver_schema."""
        from bioetl.composition.registry import PipelineFactoryProtocol

        # Check annotations or attributes
        hints = typing.get_type_hints(PipelineFactoryProtocol)

        assert "pipeline_name" in hints, (
            "PipelineFactoryProtocol MUST have pipeline_name"
        )
        assert "silver_schema" in hints, (
            "PipelineFactoryProtocol MUST have silver_schema"
        )

    def test_pipeline_factory_protocol_has_create_methods(self) -> None:
        """PipelineFactoryProtocol must have create_with_services and create_runner."""
        from bioetl.composition.registry import PipelineFactoryProtocol

        assert hasattr(PipelineFactoryProtocol, "create_with_services"), (
            "PipelineFactoryProtocol MUST have create_with_services()"
        )
        assert hasattr(PipelineFactoryProtocol, "create_runner"), (
            "PipelineFactoryProtocol MUST have create_runner()"
        )
