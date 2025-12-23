"""Tests for GenericPipelineFactory and DataSourceRegistry."""

from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.data_source_registry import (
    DataSourceRegistry,
    create_chembl_data_source,
    create_pubchem_data_source,
)
from bioetl.composition.factories.generic_factory import (
    GenericPipelineFactory,
    create_pipeline_factory,
)
from bioetl.composition.registry import PipelineRegistry


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
        """Test registering a custom provider."""

        def custom_creator(settings, config, logger, filter_config=None):
            return MagicMock()

        DataSourceRegistry.register("custom", custom_creator)
        assert "custom" in DataSourceRegistry.list_providers()

        creator = DataSourceRegistry.get("custom")
        assert creator is custom_creator

        # Cleanup
        del DataSourceRegistry._creators["custom"]


class TestDataSourceCreators:
    """Tests for individual data source creator functions."""

    @patch("bioetl.composition.factories.data_source_registry.HttpClientFactory")
    @patch("bioetl.composition.factories.data_source_registry.DataSourceFactory")
    def test_create_chembl_data_source(
        self,
        mock_ds_factory,
        mock_http_factory,
        mock_settings,
        mock_pipeline_config,
        mock_logger,
    ):
        """Test ChEMBL data source creation."""
        mock_http_client = MagicMock()
        mock_http_factory.create_for_provider.return_value = mock_http_client
        mock_adapter = MagicMock()
        mock_ds_factory.create.return_value = mock_adapter

        result = create_chembl_data_source(
            mock_settings, mock_pipeline_config, mock_logger
        )

        mock_http_factory.create_for_provider.assert_called_once_with(
            "chembl", mock_settings
        )
        mock_ds_factory.create.assert_called_once_with(
            "chembl", http_client=mock_http_client, logger=mock_logger
        )
        assert result is mock_adapter

    @patch("bioetl.composition.factories.data_source_registry.DataSourceFactory")
    def test_create_pubchem_data_source(
        self, mock_ds_factory, mock_settings, mock_pipeline_config, mock_logger
    ):
        """Test PubChem data source creation."""
        mock_adapter = MagicMock()
        mock_ds_factory.create.return_value = mock_adapter

        result = create_pubchem_data_source(
            mock_settings, mock_pipeline_config, mock_logger
        )

        mock_ds_factory.create.assert_called_once_with(
            "pubchem",
            http_client=None,
            logger=mock_logger,
            rate=5.0,
            strict_error_handling=mock_settings.strict_error_handling,
        )
        assert result is mock_adapter


class TestGenericPipelineFactory:
    """Tests for GenericPipelineFactory."""

    def test_init_with_provider(self):
        """Test factory initialization with provider name."""
        mock_pipeline_class = MagicMock()
        mock_transformer_class = MagicMock()

        factory = GenericPipelineFactory(
            pipeline_name="test_pipeline",
            pipeline_class=mock_pipeline_class,
            provider="chembl",
            transformer_class=mock_transformer_class,
        )

        assert factory.pipeline_name == "test_pipeline"
        assert factory.pipeline_class is mock_pipeline_class
        assert factory.provider == "chembl"
        assert factory.transformer_class is mock_transformer_class
        assert factory.silver_schema is None

    def test_init_with_custom_creator(self):
        """Test factory initialization with custom data source creator."""
        mock_pipeline_class = MagicMock()
        mock_transformer_class = MagicMock()
        custom_creator = MagicMock()

        factory = GenericPipelineFactory(
            pipeline_name="test_pipeline",
            pipeline_class=mock_pipeline_class,
            provider="custom",
            transformer_class=mock_transformer_class,
            data_source_creator=custom_creator,
        )

        assert factory._create_data_source is custom_creator

    def test_create_data_source(
        self, mock_settings, mock_pipeline_config, mock_logger
    ):
        """Test data source creation through factory."""
        mock_pipeline_class = MagicMock()
        mock_transformer_class = MagicMock()
        mock_data_source = MagicMock()
        custom_creator = MagicMock(return_value=mock_data_source)

        factory = GenericPipelineFactory(
            pipeline_name="test_pipeline",
            pipeline_class=mock_pipeline_class,
            provider="custom",
            transformer_class=mock_transformer_class,
            data_source_creator=custom_creator,
        )

        result = factory.create_data_source(
            mock_settings, mock_pipeline_config, mock_logger
        )

        custom_creator.assert_called_once_with(
            mock_settings, mock_pipeline_config, mock_logger, None
        )
        assert result is mock_data_source

    @patch("bioetl.composition.factories.generic_factory.load_pipeline_config")
    @patch("bioetl.composition.factories.generic_factory.BaseServicesFactory")
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
        mock_transformer_class = MagicMock()
        mock_data_source = MagicMock()
        custom_creator = MagicMock(return_value=mock_data_source)
        mock_services = MagicMock()
        mock_services_factory.create_common_services.return_value = mock_services
        mock_load_config.return_value = mock_pipeline_config

        factory = GenericPipelineFactory(
            pipeline_name="test_pipeline",
            pipeline_class=mock_pipeline_class,
            provider="custom",
            transformer_class=mock_transformer_class,
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
        mock_transformer_class = MagicMock()
        mock_schema = MagicMock()

        factory = create_pipeline_factory(
            pipeline_name="test",
            pipeline_class=mock_pipeline_class,
            provider="chembl",
            transformer_class=mock_transformer_class,
            silver_schema=mock_schema,
        )

        assert isinstance(factory, GenericPipelineFactory)
        assert factory.pipeline_name == "test"
        assert factory.pipeline_class is mock_pipeline_class
        assert factory.provider == "chembl"
        assert factory.transformer_class is mock_transformer_class
        assert factory.silver_schema is mock_schema


class TestPipelineRegistryIntegration:
    """Integration tests for PipelineRegistry with GenericPipelineFactory."""

    def test_register_factory_instance(self):
        """Test registering factory instance with registry."""
        mock_pipeline_class = MagicMock()
        mock_transformer_class = MagicMock()
        mock_schema = MagicMock()

        factory = GenericPipelineFactory(
            pipeline_name="test_generic",
            pipeline_class=mock_pipeline_class,
            provider="chembl",
            transformer_class=mock_transformer_class,
            silver_schema=mock_schema,
            data_source_creator=MagicMock(),
        )

        PipelineRegistry.register_factory(factory)

        definition = PipelineRegistry.get("test_generic")
        assert definition.factory is factory
        assert definition.silver_schema is mock_schema

        # Cleanup
        del PipelineRegistry._registry["test_generic"]
