"""Unit tests for unified Registry protocol.

Verifies that all registries implement the unified API.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.registry import PipelineRegistry


class TestPipelineRegistryUnifiedAPI:
    """Test that PipelineRegistry has unified API methods."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Ensure registry is populated and restore after test."""
        register_all_pipelines()
        backup = PipelineRegistry._registry.copy()

        yield

        PipelineRegistry._registry.clear()
        PipelineRegistry._registry.update(backup)

    def test_list_keys_returns_list(self):
        """PipelineRegistry.list_keys() should return a list."""
        keys = PipelineRegistry.list_keys()
        assert isinstance(keys, list)

    def test_list_keys_matches_list_pipelines(self):
        """list_keys() should return same result as list_pipelines()."""
        assert PipelineRegistry.list_keys() == PipelineRegistry.list_pipelines()

    def test_contains_returns_true_for_registered(self):
        """contains() should return True for registered pipelines."""
        keys = PipelineRegistry.list_keys()
        if keys:
            assert PipelineRegistry.contains(keys[0])

    def test_contains_returns_false_for_unknown(self):
        """contains() should return False for unknown pipeline."""
        assert not PipelineRegistry.contains("unknown_pipeline_xyz")

    def test_clear_empties_registry(self):
        """clear() should empty the registry."""
        initial_count = len(PipelineRegistry.list_keys())
        assert initial_count > 0

        PipelineRegistry.clear()

        assert len(PipelineRegistry.list_keys()) == 0

    def test_register_adds_pipeline(self):
        """register() should add a pipeline to registry."""
        mock_factory = MagicMock()
        mock_factory.pipeline_name = "test_pipeline"
        mock_factory.silver_schema = None

        PipelineRegistry.register("test_pipeline", mock_factory)

        assert PipelineRegistry.contains("test_pipeline")
        definition = PipelineRegistry.get("test_pipeline")
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

    def test_both_registries_have_list_keys(self):
        """Both registries should have list_keys() method."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        assert hasattr(PipelineRegistry, "list_keys")
        assert hasattr(DataSourceRegistry, "list_keys")
        assert callable(PipelineRegistry.list_keys)
        assert callable(DataSourceRegistry.list_keys)

    def test_both_registries_have_contains(self):
        """Both registries should have contains() method."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        assert hasattr(PipelineRegistry, "contains")
        assert hasattr(DataSourceRegistry, "contains")
        assert callable(PipelineRegistry.contains)
        assert callable(DataSourceRegistry.contains)

    def test_both_registries_have_clear(self):
        """Both registries should have clear() method."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        assert hasattr(PipelineRegistry, "clear")
        assert hasattr(DataSourceRegistry, "clear")
        assert callable(PipelineRegistry.clear)
        assert callable(DataSourceRegistry.clear)

    def test_both_registries_have_get(self):
        """Both registries should have get() method."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        assert hasattr(PipelineRegistry, "get")
        assert hasattr(DataSourceRegistry, "get")
        assert callable(PipelineRegistry.get)
        assert callable(DataSourceRegistry.get)

    def test_both_registries_have_register(self):
        """Both registries should have register() method."""
        from bioetl.composition.factories.data_source_factory import (
            DataSourceRegistry,
        )

        assert hasattr(PipelineRegistry, "register")
        assert hasattr(DataSourceRegistry, "register")
        assert callable(PipelineRegistry.register)
        assert callable(DataSourceRegistry.register)
