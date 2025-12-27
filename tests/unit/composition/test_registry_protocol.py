"""Unit tests for unified Registry protocol.

Verifies that all registries implement the unified API.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.pipeline_factories import register_all_pipelines


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


class TestDataSourceRegistryUnifiedAPI:
    """Test that DataSourceRegistry has unified API methods."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Restore registry after test."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        backup = DataSourceRegistry._creators.copy()

        yield

        DataSourceRegistry._creators.clear()
        DataSourceRegistry._creators.update(backup)

    def test_list_keys_returns_list(self):
        """DataSourceRegistry.list_keys() should return a list."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        keys = DataSourceRegistry.list_keys()
        assert isinstance(keys, list)

    def test_list_keys_matches_list_providers(self):
        """list_keys() should return same result as list_providers()."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        assert DataSourceRegistry.list_keys() == DataSourceRegistry.list_providers()

    def test_contains_returns_true_for_registered(self):
        """contains() should return True for registered providers."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        assert DataSourceRegistry.contains("chembl")

    def test_contains_returns_false_for_unknown(self):
        """contains() should return False for unknown provider."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        assert not DataSourceRegistry.contains("unknown_provider_xyz")

    def test_clear_empties_registry(self):
        """clear() should empty the registry."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        # DataSourceRegistry now delegates to ProviderRegistry,
        # so _creators is not used. Test that list_keys works correctly.
        keys_before = DataSourceRegistry.list_keys()
        assert len(keys_before) > 0

        DataSourceRegistry.clear()

        # After clear, local _creators should be empty
        assert len(DataSourceRegistry._creators) == 0

    def test_get_raises_keyerror_for_unknown(self):
        """get() should raise KeyError for unknown provider."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        with pytest.raises(KeyError):
            DataSourceRegistry.get("unknown_provider_xyz")


class TestUnifiedAPIConsistency:
    """Test that all registries have consistent API."""

    @pytest.fixture(autouse=True)
    def setup_registry(self, isolated_registry):
        """Use isolated registry for tests."""
        register_all_pipelines(registry=isolated_registry)
        self.registry = isolated_registry
        yield

    def test_both_registries_have_list_keys(self):
        """Both registries should have list_keys() method."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        assert hasattr(self.registry, "list_keys")
        assert hasattr(DataSourceRegistry, "list_keys")
        assert callable(self.registry.list_keys)
        assert callable(DataSourceRegistry.list_keys)

    def test_both_registries_have_contains(self):
        """Both registries should have contains() method."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        assert hasattr(self.registry, "contains")
        assert hasattr(DataSourceRegistry, "contains")
        assert callable(self.registry.contains)
        assert callable(DataSourceRegistry.contains)

    def test_both_registries_have_clear(self):
        """Both registries should have clear() method."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        assert hasattr(self.registry, "clear")
        assert hasattr(DataSourceRegistry, "clear")
        assert callable(self.registry.clear)
        assert callable(DataSourceRegistry.clear)

    def test_both_registries_have_get(self):
        """Both registries should have get() method."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        assert hasattr(self.registry, "get")
        assert hasattr(DataSourceRegistry, "get")
        assert callable(self.registry.get)
        assert callable(DataSourceRegistry.get)

    def test_both_registries_have_register(self):
        """Both registries should have register() method."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        assert hasattr(self.registry, "register")
        assert hasattr(DataSourceRegistry, "register")
        assert callable(self.registry.register)
        assert callable(DataSourceRegistry.register)
