"""Tests for Registry pattern contracts.

Verifies that all registries follow the unified BaseRegistry protocol.
Implements CLAUDE.md §6.3.3 requirements.

Updated for instance-level PipelineRegistry (2025-12).
"""

from __future__ import annotations

import typing

import pytest

from bioetl.composition.registry import PipelineRegistry, get_default_registry


class TestRegistryProtocol:
    """All registries must implement BaseRegistry protocol."""

    def test_pipeline_registry_has_required_methods(self) -> None:
        """PipelineRegistry must have get, register_factory, list_pipelines methods."""
        # Check class-level methods exist
        registry = PipelineRegistry()
        assert hasattr(registry, "get"), "PipelineRegistry MUST have get() method"
        assert hasattr(registry, "register_factory"), (
            "PipelineRegistry MUST have register_factory() method"
        )
        assert hasattr(registry, "list_pipelines"), (
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

    def test_pipeline_registry_raises_on_missing(self, isolated_registry) -> None:
        """PipelineRegistry raises RuntimeError or ValueError for unknown pipeline."""
        # Empty registry raises RuntimeError
        with pytest.raises((RuntimeError, ValueError, KeyError)):
            isolated_registry.get("nonexistent_pipeline_12345")

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


class TestRegistryInstanceVariables:
    """PipelineRegistry uses instance variables for test isolation."""

    def test_pipeline_registry_has_instance_registry(self) -> None:
        """PipelineRegistry._registry must be an instance variable."""
        registry = PipelineRegistry()

        # Instance should have _registry attribute
        assert hasattr(registry, "_registry"), (
            "PipelineRegistry MUST have _registry attribute"
        )

        # It should be a dict
        assert isinstance(registry._registry, dict), (
            "PipelineRegistry._registry MUST be a dict"
        )

    def test_pipeline_registry_has_instance_lock(self) -> None:
        """PipelineRegistry._lock must be an instance variable."""
        import threading

        registry = PipelineRegistry()

        # Instance should have _lock attribute
        assert hasattr(registry, "_lock"), "PipelineRegistry MUST have _lock attribute"

        # It should be an RLock
        assert isinstance(registry._lock, type(threading.RLock())), (
            "PipelineRegistry._lock MUST be an RLock"
        )

    def test_pipeline_registry_instances_are_independent(self) -> None:
        """Two PipelineRegistry instances must have separate storage."""
        registry1 = PipelineRegistry()
        registry2 = PipelineRegistry()

        # Should be different dict instances
        assert registry1._registry is not registry2._registry, (
            "PipelineRegistry instances MUST have independent _registry"
        )

        # Should be different lock instances
        assert registry1._lock is not registry2._lock, (
            "PipelineRegistry instances MUST have independent _lock"
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

    def test_pipeline_registry_list_returns_list(
        self, populated_isolated_registry
    ) -> None:
        """PipelineRegistry.list_pipelines must return list[str]."""
        result = populated_isolated_registry.list_pipelines()
        assert isinstance(result, list), "list_pipelines() MUST return a list"
        # All items should be strings
        for item in result:
            assert isinstance(item, str), "list_pipelines() MUST return list of strings"

    def test_datasource_registry_list_returns_list(self) -> None:
        """DataSourceRegistry.list_providers must return list[str]."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        result = DataSourceRegistry.list_providers()
        assert isinstance(result, list), "list_providers() MUST return a list"
        for item in result:
            assert isinstance(item, str), "list_providers() MUST return list of strings"

    def test_provider_registry_list_returns_sorted_list(self) -> None:
        """ProviderRegistry.list_providers must return sorted list[str]."""
        from bioetl.composition.providers.provider_registry import ProviderRegistry

        result = ProviderRegistry.list_providers()
        assert isinstance(result, list), "list_providers() MUST return a list"
        # Check it's sorted
        assert result == sorted(result), "list_providers() MUST return sorted list"


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
            assert provider in providers, f"DataSourceRegistry MUST include {provider}"


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


class TestDefaultRegistryHelper:
    """Test get_default_registry() helper function."""

    def test_get_default_registry_returns_instance(self) -> None:
        """get_default_registry() must return a PipelineRegistry instance."""
        registry = get_default_registry()
        assert isinstance(registry, PipelineRegistry), (
            "get_default_registry() MUST return PipelineRegistry instance"
        )

    def test_get_default_registry_returns_same_instance(self) -> None:
        """get_default_registry() must return the same instance on multiple calls."""
        registry1 = get_default_registry()
        registry2 = get_default_registry()
        assert registry1 is registry2, (
            "get_default_registry() MUST return the same instance"
        )

    def test_create_registry_returns_new_instance(self) -> None:
        """create_registry() must return a new instance each time."""
        from bioetl.composition.registry import create_registry

        registry1 = create_registry()
        registry2 = create_registry()
        assert registry1 is not registry2, (
            "create_registry() MUST return a new instance"
        )
