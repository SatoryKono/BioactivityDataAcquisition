"""Unit tests for canonical registry and datasource-helper surfaces."""

from __future__ import annotations

from inspect import signature
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.pipeline.registry import register_all_pipelines


pytestmark = pytest.mark.unit

class TestPipelineRegistryUnifiedAPI:
    """Test that PipelineRegistry has unified API methods."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, isolated_registry):
        """Ensure registry is populated using isolated registry."""
        register_all_pipelines(registry=isolated_registry)
        self.registry = isolated_registry
        yield

    def test_list_keys_returns_list(self):
        """PipelineRegistry.list_keys() should return a list."""
        keys = self.registry.list_keys()
        assert isinstance(keys, list)

    def test_list_keys_matches_list_pipelines(self):
        """list_keys() should return same result as list_pipelines()."""
        assert self.registry.list_keys() == self.registry.list_pipelines()

    def test_contains_returns_true_for_registered(self):
        """contains() should return True for registered pipelines."""
        keys = self.registry.list_keys()
        if keys:
            assert self.registry.contains(keys[0])

    def test_contains_returns_false_for_unknown(self):
        """contains() should return False for unknown pipeline."""
        assert not self.registry.contains("unknown_pipeline_xyz")

    def test_clear_empties_registry(self):
        """clear() should empty the registry."""
        initial_count = len(self.registry.list_keys())
        assert initial_count > 0

        self.registry.clear()

        assert len(self.registry.list_keys()) == 0

    def test_register_adds_pipeline(self):
        """register() should add a pipeline to registry."""
        # Clear first and register a new pipeline
        self.registry.clear()

        mock_factory = MagicMock()
        mock_factory.pipeline_name = "test_pipeline"
        mock_factory.silver_schema = None
        mock_factory.gold_schema = MagicMock()  # Required

        self.registry.register("test_pipeline", mock_factory)

        assert self.registry.contains("test_pipeline")
        definition = self.registry.get("test_pipeline")
        assert definition.factory is mock_factory

    def test_register_rejects_mismatched_key(self):
        """register() should reject keys that drift from factory.pipeline_name."""
        self.registry.clear()

        mock_factory = MagicMock()
        mock_factory.pipeline_name = "actual_pipeline"
        mock_factory.silver_schema = None
        mock_factory.gold_schema = MagicMock()

        with pytest.raises(ValueError, match="does not match"):
            self.registry.register("different_pipeline", mock_factory)


class TestDataSourceCreatorHelper:
    """Canonical datasource helper should bind provider-specific creators."""

    @pytest.fixture(autouse=True)
    def setup_registry(self, isolated_registry):
        """Populate isolated pipeline registry for pipeline-side checks."""
        register_all_pipelines(registry=isolated_registry)
        self.registry = isolated_registry
        yield

    def test_provider_registry_has_list_keys(self):
        """ProviderRegistry should retain the unified list_keys() surface."""
        from bioetl.composition.providers.provider_registry import ProviderRegistry

        assert hasattr(self.registry, "list_keys")
        assert hasattr(ProviderRegistry, "list_keys")
        assert callable(self.registry.list_keys)
        assert callable(ProviderRegistry.list_keys)

    def test_provider_registry_has_contains(self):
        """ProviderRegistry should retain the unified contains() surface."""
        from bioetl.composition.providers.provider_registry import ProviderRegistry

        assert hasattr(self.registry, "contains")
        assert hasattr(ProviderRegistry, "contains")
        assert callable(self.registry.contains)
        assert callable(ProviderRegistry.contains)

    def test_provider_registry_has_clear(self):
        """ProviderRegistry should retain the unified clear() surface."""
        from bioetl.composition.providers.provider_registry import ProviderRegistry

        assert hasattr(self.registry, "clear")
        assert hasattr(ProviderRegistry, "clear")
        assert callable(self.registry.clear)
        assert callable(ProviderRegistry.clear)

    def test_get_data_source_creator_returns_callable(self):
        """Canonical helper should return a provider-bound creator callable."""
        from bioetl.composition.factories.datasource.data_source_factory import (
            get_data_source_creator,
        )
        from bioetl.composition.providers import ensure_providers_loaded

        ensure_providers_loaded()
        creator = get_data_source_creator("chembl")

        assert callable(creator)

    def test_get_data_source_creator_raises_keyerror_for_unknown_provider(self):
        """Canonical helper should raise KeyError for unknown providers."""
        from bioetl.composition.factories.datasource.data_source_factory import (
            get_data_source_creator,
        )
        from bioetl.composition.providers import ensure_providers_loaded

        ensure_providers_loaded()

        with pytest.raises(KeyError):
            get_data_source_creator("unknown_provider_xyz")

    def test_get_data_source_creator_matches_protocol_signature(self):
        """Bound creator should expose the canonical datasource protocol signature."""
        from bioetl.composition.factories.datasource.data_source_factory import (
            get_data_source_creator,
        )
        from bioetl.composition.providers import ensure_providers_loaded

        ensure_providers_loaded()
        creator = get_data_source_creator("chembl")
        param_names = set(signature(creator).parameters)

        assert {
            "settings",
            "pipeline_config",
            "logger",
            "filter_config",
            "metrics",
            "pipeline_name",
        } <= param_names

    def test_pipeline_registry_has_register(self):
        """PipelineRegistry should keep register() as the canonical pipeline seam."""
        assert hasattr(self.registry, "register")
        assert callable(self.registry.register)
