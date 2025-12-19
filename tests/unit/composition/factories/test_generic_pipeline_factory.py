"""Unit tests for GenericPipelineFactory and DataSourceRegistry.

Tests the new unified factory infrastructure that eliminates boilerplate
in per-pipeline factory classes.
"""

from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.types import RunType


@pytest.fixture
def mock_settings():
    """Create mock application settings."""
    settings = MagicMock()
    settings.env = "staging"
    settings.strict_error_handling = False
    settings.aws = MagicMock()
    settings.aws.endpoint_url = None
    settings.aws.region = "us-east-1"
    settings.aws.access_key_id = None
    settings.aws.secret_access_key = None
    settings.s3 = MagicMock()
    settings.s3.bucket_bronze = "bronze"
    settings.s3.bucket_silver = "silver"
    settings.s3.bucket_gold = "gold"
    settings.s3.bucket_checkpoints = "checkpoints"
    settings.storage_options = {}
    settings.metrics = None
    settings.pubmed_api_key = None
    settings.default_email = "test@example.com"
    return settings


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def mock_pipeline_config():
    """Create mock pipeline configuration."""
    config = MagicMock()
    config.source = MagicMock()
    config.source.get = MagicMock(return_value={})
    config.source.api_key = None
    config.source.email = None
    return config


@pytest.fixture
def mock_services():
    """Create mock PipelineServices."""
    services = MagicMock()
    services.data_source = MagicMock()
    services.storage = MagicMock()
    services.lock = MagicMock()
    services.checkpoint = MagicMock()
    services.quarantine = MagicMock()
    services.metrics = MagicMock()
    services.logger = MagicMock()
    return services


# =============================================================================
# DataSourceRegistry Tests
# =============================================================================


@pytest.mark.unit
class TestDataSourceRegistry:
    """Tests for DataSourceRegistry."""

    def test_list_providers_returns_all_registered(self):
        """Test list_providers returns all registered providers."""
        from bioetl.composition.factories.data_source_registry import (
            DataSourceRegistry,
        )

        providers = DataSourceRegistry.list_providers()
        assert "chembl" in providers
        assert "pubchem" in providers
        assert "uniprot" in providers
        assert "pubmed" in providers

    def test_get_returns_creator_for_known_provider(self):
        """Test get returns a callable for known providers."""
        from bioetl.composition.factories.data_source_registry import (
            DataSourceRegistry,
        )

        creator = DataSourceRegistry.get("chembl")
        assert callable(creator)

    def test_get_raises_for_unknown_provider(self):
        """Test get raises KeyError for unknown provider."""
        from bioetl.composition.factories.data_source_registry import (
            DataSourceRegistry,
        )

        with pytest.raises(KeyError, match="Unknown provider: unknown"):
            DataSourceRegistry.get("unknown")

    def test_register_adds_new_provider(self):
        """Test register adds a new provider creator."""
        from bioetl.composition.factories.data_source_registry import (
            DataSourceRegistry,
        )

        mock_creator = MagicMock()
        DataSourceRegistry.register("test_provider", mock_creator)

        assert "test_provider" in DataSourceRegistry.list_providers()
        assert DataSourceRegistry.get("test_provider") is mock_creator

        # Cleanup
        del DataSourceRegistry._creators["test_provider"]

    @patch("bioetl.composition.factories.data_source_registry.HttpClientFactory")
    @patch("bioetl.composition.factories.data_source_registry.DataSourceFactory")
    def test_create_calls_creator_with_args(
        self,
        mock_ds_factory,
        _mock_http_factory,
        mock_settings,
        mock_pipeline_config,
    ):
        """Test create convenience method calls creator with correct args."""
        from bioetl.composition.factories.data_source_registry import (
            DataSourceRegistry,
        )

        mock_adapter = MagicMock()
        mock_ds_factory.create.return_value = mock_adapter

        result = DataSourceRegistry.create(
            "chembl",
            mock_settings,
            mock_pipeline_config,
        )

        assert result is mock_adapter
        mock_ds_factory.create.assert_called_once()


# =============================================================================
# GenericPipelineFactory Tests
# =============================================================================


@pytest.mark.unit
class TestGenericPipelineFactory:
    """Tests for GenericPipelineFactory."""

    def test_init_stores_attributes(self):
        """Test constructor stores all attributes correctly."""
        from bioetl.composition.factories.generic_pipeline_factory import (
            GenericPipelineFactory,
        )

        mock_pipeline_class = MagicMock()
        mock_schema = MagicMock()

        factory = GenericPipelineFactory(
            pipeline_class=mock_pipeline_class,
            pipeline_name="test_pipeline",
            provider="chembl",
            silver_schema=mock_schema,
        )

        assert factory.pipeline_class is mock_pipeline_class
        assert factory.pipeline_name == "test_pipeline"
        assert factory.provider == "chembl"
        assert factory.silver_schema is mock_schema

    def test_init_with_custom_data_source_creator(self):
        """Test constructor accepts custom data source creator."""
        from bioetl.composition.factories.generic_pipeline_factory import (
            GenericPipelineFactory,
        )

        mock_pipeline_class = MagicMock()
        custom_creator = MagicMock()

        factory = GenericPipelineFactory(
            pipeline_class=mock_pipeline_class,
            pipeline_name="test_pipeline",
            provider="chembl",
            data_source_creator=custom_creator,
        )

        # Verify custom creator is used
        creator = factory._get_data_source_creator()
        assert creator is custom_creator

    @patch("bioetl.composition.factories.generic_pipeline_factory.DataSourceRegistry")
    def test_get_data_source_creator_uses_registry_by_default(
        self,
        mock_registry,
    ):
        """Test _get_data_source_creator uses registry when no custom creator."""
        from bioetl.composition.factories.generic_pipeline_factory import (
            GenericPipelineFactory,
        )

        mock_pipeline_class = MagicMock()
        mock_creator = MagicMock()
        mock_registry.get.return_value = mock_creator

        factory = GenericPipelineFactory(
            pipeline_class=mock_pipeline_class,
            pipeline_name="test_pipeline",
            provider="chembl",
        )

        result = factory._get_data_source_creator()

        mock_registry.get.assert_called_once_with("chembl")
        assert result is mock_creator

    @patch("bioetl.composition.factories.generic_pipeline_factory.DataSourceRegistry")
    def test_create_data_source_calls_creator(
        self,
        mock_registry,
        mock_settings,
        mock_pipeline_config,
    ):
        """Test create_data_source calls the creator with correct arguments."""
        from bioetl.composition.factories.generic_pipeline_factory import (
            GenericPipelineFactory,
        )

        mock_pipeline_class = MagicMock()
        mock_creator = MagicMock()
        mock_data_source = MagicMock()
        mock_creator.return_value = mock_data_source
        mock_registry.get.return_value = mock_creator

        factory = GenericPipelineFactory(
            pipeline_class=mock_pipeline_class,
            pipeline_name="test_pipeline",
            provider="chembl",
        )

        result = factory.create_data_source(
            mock_settings,
            mock_pipeline_config,
            filter_config=None,
        )

        mock_creator.assert_called_once_with(
            mock_settings, mock_pipeline_config, None
        )
        assert result is mock_data_source

    @patch("bioetl.composition.factories.generic_pipeline_factory.BaseServicesFactory")
    @patch("bioetl.composition.factories.generic_pipeline_factory.DataSourceRegistry")
    @patch("bioetl.composition.factories.generic_pipeline_factory.load_pipeline_config")
    def test_build_services_creates_services(
        self,
        mock_load_config,
        mock_registry,
        mock_base_services,
        mock_settings,
        mock_logger,
        mock_pipeline_config,
        mock_services,
    ):
        """Test build_services creates PipelineServices correctly."""
        from bioetl.composition.factories.generic_pipeline_factory import (
            GenericPipelineFactory,
        )

        mock_pipeline_class = MagicMock()
        mock_data_source = MagicMock()
        mock_creator = MagicMock(return_value=mock_data_source)
        mock_registry.get.return_value = mock_creator
        mock_load_config.return_value = mock_pipeline_config
        mock_base_services.create_common_services.return_value = mock_services

        factory = GenericPipelineFactory(
            pipeline_class=mock_pipeline_class,
            pipeline_name="test_pipeline",
            provider="chembl",
        )

        result = factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert result is mock_services
        mock_base_services.create_common_services.assert_called_once_with(
            settings=mock_settings,
            logger=mock_logger,
            data_source=mock_data_source,
            pipeline_config=mock_pipeline_config,
        )

    @patch("bioetl.composition.factories.generic_pipeline_factory.BaseServicesFactory")
    @patch("bioetl.composition.factories.generic_pipeline_factory.DataSourceRegistry")
    @patch("bioetl.composition.factories.generic_pipeline_factory.load_pipeline_config")
    def test_build_services_uses_provided_config(
        self,
        mock_load_config,
        mock_registry,
        mock_base_services,
        mock_settings,
        mock_logger,
        mock_pipeline_config,
        mock_services,
    ):
        """Test build_services uses provided config instead of loading."""
        from bioetl.composition.factories.generic_pipeline_factory import (
            GenericPipelineFactory,
        )

        mock_pipeline_class = MagicMock()
        mock_data_source = MagicMock()
        mock_creator = MagicMock(return_value=mock_data_source)
        mock_registry.get.return_value = mock_creator
        mock_base_services.create_common_services.return_value = mock_services

        factory = GenericPipelineFactory(
            pipeline_class=mock_pipeline_class,
            pipeline_name="test_pipeline",
            provider="chembl",
        )

        factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
            config=mock_pipeline_config,
        )

        # Should NOT call load_pipeline_config when config is provided
        mock_load_config.assert_not_called()

    @patch("bioetl.composition.factories.generic_pipeline_factory.yaml_config_to_domain")
    @patch("bioetl.composition.factories.generic_pipeline_factory.BaseServicesFactory")
    @patch("bioetl.composition.factories.generic_pipeline_factory.DataSourceRegistry")
    @patch("bioetl.composition.factories.generic_pipeline_factory.load_pipeline_config")
    def test_create_with_services_creates_pipeline(
        self,
        mock_load_config,
        mock_registry,
        mock_base_services,
        mock_yaml_to_domain,
        mock_settings,
        mock_logger,
        mock_pipeline_config,
        mock_services,
    ):
        """Test create_with_services creates pipeline instance."""
        from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
        from bioetl.composition.factories.generic_pipeline_factory import (
            GenericPipelineFactory,
        )

        mock_pipeline_class = MagicMock()
        mock_pipeline_instance = MagicMock()
        mock_pipeline_class.create.return_value = mock_pipeline_instance

        mock_data_source = MagicMock()
        mock_creator = MagicMock(return_value=mock_data_source)
        mock_registry.get.return_value = mock_creator
        mock_load_config.return_value = mock_pipeline_config
        mock_base_services.create_common_services.return_value = mock_services

        mock_domain_config = MagicMock()
        mock_yaml_to_domain.return_value = mock_domain_config

        factory = GenericPipelineFactory(
            pipeline_class=mock_pipeline_class,
            pipeline_name="test_pipeline",
            provider="chembl",
        )

        runtime = PipelineRuntimeConfig(run_type=RunType.INCREMENTAL)
        result = factory.create_with_services(
            runtime=runtime,
            settings=mock_settings,
            logger=mock_logger,
        )

        assert result is mock_pipeline_instance
        mock_pipeline_class.create.assert_called_once_with(
            runtime=runtime,
            services=mock_services,
            config=mock_domain_config,
        )


# =============================================================================
# create_pipeline_factory Helper Tests
# =============================================================================


@pytest.mark.unit
class TestCreatePipelineFactoryHelper:
    """Tests for create_pipeline_factory convenience function."""

    def test_creates_generic_pipeline_factory(self):
        """Test create_pipeline_factory returns GenericPipelineFactory."""
        from bioetl.composition.factories.generic_pipeline_factory import (
            GenericPipelineFactory,
            create_pipeline_factory,
        )

        mock_pipeline_class = MagicMock()
        mock_schema = MagicMock()

        factory = create_pipeline_factory(
            pipeline_class=mock_pipeline_class,
            pipeline_name="test_pipeline",
            provider="chembl",
            silver_schema=mock_schema,
        )

        assert isinstance(factory, GenericPipelineFactory)
        assert factory.pipeline_class is mock_pipeline_class
        assert factory.pipeline_name == "test_pipeline"
        assert factory.provider == "chembl"
        assert factory.silver_schema is mock_schema


# =============================================================================
# Factory Instance Tests
# =============================================================================


@pytest.mark.unit
class TestFactoryInstances:
    """Tests for pre-configured factory instances."""

    def test_chembl_activity_factory_is_generic_pipeline_factory(self):
        """Test chembl_activity_factory is a GenericPipelineFactory."""
        from bioetl.composition.factories import chembl_activity_factory
        from bioetl.composition.factories.generic_pipeline_factory import (
            GenericPipelineFactory,
        )

        assert isinstance(chembl_activity_factory, GenericPipelineFactory)
        assert chembl_activity_factory.pipeline_name == "chembl_activity"
        assert chembl_activity_factory.provider == "chembl"

    def test_pubchem_compound_factory_is_generic_pipeline_factory(self):
        """Test pubchem_compound_factory is a GenericPipelineFactory."""
        from bioetl.composition.factories import pubchem_compound_factory
        from bioetl.composition.factories.generic_pipeline_factory import (
            GenericPipelineFactory,
        )

        assert isinstance(pubchem_compound_factory, GenericPipelineFactory)
        assert pubchem_compound_factory.pipeline_name == "pubchem_compound"
        assert pubchem_compound_factory.provider == "pubchem"

    def test_uniprot_protein_factory_is_generic_pipeline_factory(self):
        """Test uniprot_protein_factory is a GenericPipelineFactory."""
        from bioetl.composition.factories import uniprot_protein_factory
        from bioetl.composition.factories.generic_pipeline_factory import (
            GenericPipelineFactory,
        )

        assert isinstance(uniprot_protein_factory, GenericPipelineFactory)
        assert uniprot_protein_factory.pipeline_name == "uniprot_protein"
        assert uniprot_protein_factory.provider == "uniprot"

    def test_pubmed_publications_factory_is_generic_pipeline_factory(self):
        """Test pubmed_publications_factory is a GenericPipelineFactory."""
        from bioetl.composition.factories import pubmed_publications_factory
        from bioetl.composition.factories.generic_pipeline_factory import (
            GenericPipelineFactory,
        )

        assert isinstance(pubmed_publications_factory, GenericPipelineFactory)
        assert pubmed_publications_factory.pipeline_name == "pubmed_publications"
        assert pubmed_publications_factory.provider == "pubmed"


# =============================================================================
# Deprecated Class Tests
# =============================================================================


@pytest.mark.unit
class TestDeprecatedClasses:
    """Tests for deprecated factory classes."""

    def test_chembl_activity_pipeline_factory_emits_deprecation_warning(self):
        """Test ChEMBLActivityPipelineFactory emits deprecation warning."""
        from bioetl.composition.factories.chembl_activity import (
            ChEMBLActivityPipelineFactory,
        )

        with pytest.warns(DeprecationWarning, match="ChEMBLActivityPipelineFactory is deprecated"):
            ChEMBLActivityPipelineFactory()

    def test_pubchem_compound_pipeline_factory_emits_deprecation_warning(self):
        """Test PubChemCompoundPipelineFactory emits deprecation warning."""
        from bioetl.composition.factories.pubchem_compound import (
            PubChemCompoundPipelineFactory,
        )

        with pytest.warns(DeprecationWarning, match="PubChemCompoundPipelineFactory is deprecated"):
            PubChemCompoundPipelineFactory()

    def test_uniprot_protein_pipeline_factory_emits_deprecation_warning(self):
        """Test UniProtProteinPipelineFactory emits deprecation warning."""
        from bioetl.composition.factories.uniprot_protein import (
            UniProtProteinPipelineFactory,
        )

        with pytest.warns(DeprecationWarning, match="UniProtProteinPipelineFactory is deprecated"):
            UniProtProteinPipelineFactory()

    def test_pubmed_publications_pipeline_factory_emits_deprecation_warning(self):
        """Test PubMedPublicationsPipelineFactory emits deprecation warning."""
        from bioetl.composition.factories.pubmed_publications import (
            PubMedPublicationsPipelineFactory,
        )

        with pytest.warns(DeprecationWarning, match="PubMedPublicationsPipelineFactory is deprecated"):
            PubMedPublicationsPipelineFactory()


# =============================================================================
# Module Exports Tests
# =============================================================================


@pytest.mark.unit
class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_factories_module_exports_generic_pipeline_factory(self):
        """Test factories module exports GenericPipelineFactory."""
        from bioetl.composition import factories

        assert hasattr(factories, "GenericPipelineFactory")
        assert "GenericPipelineFactory" in factories.__all__

    def test_factories_module_exports_data_source_registry(self):
        """Test factories module exports DataSourceRegistry."""
        from bioetl.composition import factories

        assert hasattr(factories, "DataSourceRegistry")
        assert "DataSourceRegistry" in factories.__all__

    def test_factories_module_exports_factory_instances(self):
        """Test factories module exports factory instances."""
        from bioetl.composition import factories

        factory_names = [
            "chembl_activity_factory",
            "pubchem_compound_factory",
            "uniprot_protein_factory",
            "pubmed_publications_factory",
        ]

        for name in factory_names:
            assert hasattr(factories, name), f"Missing export: {name}"
            assert name in factories.__all__, f"Not in __all__: {name}"

    def test_factories_module_exports_data_source_creators(self):
        """Test factories module exports data source creator functions."""
        from bioetl.composition import factories

        creator_names = [
            "create_chembl_data_source",
            "create_pubchem_data_source",
            "create_uniprot_data_source",
            "create_pubmed_data_source",
        ]

        for name in creator_names:
            assert hasattr(factories, name), f"Missing export: {name}"
            assert name in factories.__all__, f"Not in __all__: {name}"
