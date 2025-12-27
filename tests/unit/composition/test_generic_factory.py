"""Tests for GenericPipelineFactory and DataSourceRegistry."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.data_source_factory import DataSourceRegistry
from bioetl.composition.factories.pipeline_factory import (
    GenericPipelineFactory,
    create_pipeline_factory,
)


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.strict_error_handling = False
    settings.env = "test"
    settings.pubmed_api_key = None
    settings.default_email = "test@example.com"
    return settings


@pytest.fixture
def mock_pipeline_config():
    """Create mock pipeline config."""
    config = MagicMock()
    config.source = MagicMock()
    config.source.get = MagicMock(return_value={})
    config.source.api_key = None
    config.source.email = None
    return config


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    return MagicMock()


class TestDataSourceRegistry:
    """Tests for DataSourceRegistry."""

    def test_get_known_provider(self):
        """Test getting creator for known provider."""
        creator = DataSourceRegistry.get("chembl")
        assert callable(creator)

    def test_get_unknown_provider_raises(self):
        """Test getting creator for unknown provider raises KeyError."""
        with pytest.raises(KeyError, match="Unknown provider"):
            DataSourceRegistry.get("unknown_provider")

    def test_list_providers(self):
        """Test listing all registered providers."""
        providers = DataSourceRegistry.list_providers()
        assert "chembl" in providers
        assert "pubchem" in providers
        assert "uniprot" in providers
        assert "pubmed" in providers

    def test_register_custom_provider(self):
        """Test registering a custom provider stores in local dict.

        Note: register() is deprecated. New registrations should go through
        ProviderRegistry. This test verifies backward-compat local storage only.
        """

        def custom_creator(settings, config, logger, filter_config=None):
            return MagicMock()

        DataSourceRegistry.register("custom", custom_creator)

        # Local registration stores in _creators dict
        assert "custom" in DataSourceRegistry._creators
        assert DataSourceRegistry._creators["custom"] is custom_creator

        # Cleanup
        del DataSourceRegistry._creators["custom"]


class TestGenericPipelineFactory:
    """Tests for GenericPipelineFactory."""

    def test_init_with_provider(self):
        """Test factory initialization with provider name."""
        mock_pipeline_class = MagicMock()

        factory = GenericPipelineFactory(
            pipeline_name="test_pipeline",
            pipeline_class=mock_pipeline_class,
            provider="chembl",
            gold_schema=MagicMock(),
        )

        assert factory.pipeline_name == "test_pipeline"
        assert factory.pipeline_class is mock_pipeline_class
        assert factory.provider == "chembl"
        assert factory.silver_schema is None

    def test_init_with_custom_creator(self):
        """Test factory initialization with custom data source creator."""
        mock_pipeline_class = MagicMock()
        custom_creator = MagicMock()

        factory = GenericPipelineFactory(
            pipeline_name="test_pipeline",
            pipeline_class=mock_pipeline_class,
            provider="custom",
            gold_schema=MagicMock(),
            data_source_creator=custom_creator,
        )

        assert factory._create_data_source is custom_creator

    def test_create_data_source(
        self, mock_settings, mock_pipeline_config, mock_logger
    ):
        """Test data source creation through factory."""
        mock_pipeline_class = MagicMock()
        mock_data_source = MagicMock()
        custom_creator = MagicMock(return_value=mock_data_source)

        factory = GenericPipelineFactory(
            pipeline_name="test_pipeline",
            pipeline_class=mock_pipeline_class,
            provider="custom",
            gold_schema=MagicMock(),
            data_source_creator=custom_creator,
        )

        result = factory.create_data_source(
            mock_settings, mock_pipeline_config, mock_logger
        )

        custom_creator.assert_called_once_with(
            mock_settings, mock_pipeline_config, mock_logger, None
        )
        assert result is mock_data_source

    @patch("bioetl.composition.factories.pipeline_factory.load_pipeline_config")
    @patch("bioetl.composition.factories.pipeline_factory.BaseServicesFactory")
    def test_build_services(
        self,
        mock_services_factory,
        mock_load_config,
        mock_settings,
        mock_pipeline_config,
        mock_logger,
    ):
        """Test services building."""
        mock_pipeline_class = MagicMock()
        mock_data_source = MagicMock()
        custom_creator = MagicMock(return_value=mock_data_source)
        mock_services = MagicMock()
        mock_services_factory.create_common_services.return_value = mock_services
        mock_load_config.return_value = mock_pipeline_config

        factory = GenericPipelineFactory(
            pipeline_name="test_pipeline",
            pipeline_class=mock_pipeline_class,
            provider="custom",
            gold_schema=MagicMock(),
            data_source_creator=custom_creator,
        )

        result = factory.build_services(mock_settings, mock_logger)

        mock_services_factory.create_common_services.assert_called_once()
        assert result is mock_services


class TestCreatePipelineFactory:
    """Tests for create_pipeline_factory convenience function."""

    def test_creates_generic_factory(self):
        """Test that function creates GenericPipelineFactory."""
        mock_pipeline_class = MagicMock()
        mock_schema = MagicMock()

        factory = create_pipeline_factory(
            pipeline_name="test",
            pipeline_class=mock_pipeline_class,
            provider="chembl",
            silver_schema=mock_schema,
            gold_schema=MagicMock(),
        )

        assert isinstance(factory, GenericPipelineFactory)
        assert factory.pipeline_name == "test"
        assert factory.pipeline_class is mock_pipeline_class
        assert factory.provider == "chembl"
        assert factory.silver_schema is mock_schema


class TestPipelineRegistryIntegration:
    """Integration tests for PipelineRegistry with GenericPipelineFactory."""

    def test_register_factory_instance(self, isolated_registry):
        """Test registering factory instance with registry."""
        mock_pipeline_class = MagicMock()
        mock_schema = MagicMock()

        factory = GenericPipelineFactory(
            pipeline_name="test_generic",
            pipeline_class=mock_pipeline_class,
            provider="chembl",
            silver_schema=mock_schema,
            gold_schema=MagicMock(),
            data_source_creator=MagicMock(),
        )

        isolated_registry.register_factory(factory)

        definition = isolated_registry.get("test_generic")
        assert definition.factory is factory
        assert definition.silver_schema is mock_schema
        # No cleanup needed - isolated_registry is fresh for each test
