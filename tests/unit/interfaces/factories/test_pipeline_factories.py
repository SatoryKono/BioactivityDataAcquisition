"""Unit tests for pipeline factories.

Tests that pipeline factory instances are properly exported and configured.
"""

from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# Re-exports from interfaces.factories Tests
# =============================================================================


@pytest.mark.unit
class TestInterfacesFactoriesReexports:
    """Test that interfaces.factories re-exports work correctly."""

    def test_chembl_activity_factory_reexport(self):
        """Test chembl_activity_factory is re-exported."""
        from bioetl.interfaces.factories import chembl_activity_factory

        assert chembl_activity_factory is not None
        assert hasattr(chembl_activity_factory, "build_services")
        assert hasattr(chembl_activity_factory, "create_with_services")
        assert chembl_activity_factory.pipeline_name == "chembl_activity"

    def test_pubchem_compound_factory_reexport(self):
        """Test pubchem_compound_factory is re-exported."""
        from bioetl.interfaces.factories import pubchem_compound_factory

        assert pubchem_compound_factory is not None
        assert hasattr(pubchem_compound_factory, "build_services")
        assert hasattr(pubchem_compound_factory, "create_with_services")
        assert pubchem_compound_factory.pipeline_name == "pubchem_compound"

    def test_uniprot_protein_factory_reexport(self):
        """Test uniprot_protein_factory is re-exported."""
        from bioetl.interfaces.factories import uniprot_protein_factory

        assert uniprot_protein_factory is not None
        assert hasattr(uniprot_protein_factory, "build_services")
        assert hasattr(uniprot_protein_factory, "create_with_services")
        assert uniprot_protein_factory.pipeline_name == "uniprot_protein"

    def test_pubmed_publications_factory_reexport(self):
        """Test pubmed_publications_factory is re-exported."""
        from bioetl.interfaces.factories import pubmed_publications_factory

        assert pubmed_publications_factory is not None
        assert hasattr(pubmed_publications_factory, "build_services")
        assert hasattr(pubmed_publications_factory, "create_with_services")
        assert pubmed_publications_factory.pipeline_name == "pubmed_publications"

    def test_all_exports_in_module(self):
        """Test __all__ contains expected factories."""
        from bioetl import interfaces

        factory_module = interfaces.factories
        assert "chembl_activity_factory" in factory_module.__all__
        assert "pubchem_compound_factory" in factory_module.__all__
        assert "uniprot_protein_factory" in factory_module.__all__
        assert "pubmed_publications_factory" in factory_module.__all__


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
    config.source.get = MagicMock(return_value={"rate_limit": 5.0})
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
    return services


# =============================================================================
# GenericPipelineFactory Tests (via pubchem_compound_factory)
# =============================================================================


@pytest.mark.unit
class TestPubChemCompoundFactory:
    """Tests for pubchem_compound_factory (GenericPipelineFactory instance)."""

    @patch("bioetl.composition.factories.generic_factory.BaseServicesFactory")
    @patch("bioetl.composition.factories.data_source_registry.DataSourceFactory.create")
    @patch("bioetl.composition.factories.generic_factory.load_pipeline_config")
    def test_build_services_creates_data_source(
        self,
        mock_load_config,
        mock_data_source_create,
        mock_base_services,
        mock_settings,
        mock_logger,
        mock_pipeline_config,
        mock_services,
    ):
        """Test build_services creates data source via DataSourceRegistry."""
        from bioetl.composition.factories.pipeline_factories import (
            pubchem_compound_factory,
        )

        mock_load_config.return_value = mock_pipeline_config
        mock_base_services.create_common_services.return_value = mock_services
        mock_data_source = MagicMock()
        mock_data_source_create.return_value = mock_data_source

        services = pubchem_compound_factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services is not None
        # DataSourceFactory.create is called with pubchem provider
        mock_data_source_create.assert_called_once()
        call_args = mock_data_source_create.call_args
        assert call_args[0][0] == "pubchem"

    @patch("bioetl.composition.factories.generic_factory.BaseServicesFactory")
    @patch("bioetl.composition.factories.data_source_registry.DataSourceFactory.create")
    @patch("bioetl.composition.factories.generic_factory.load_pipeline_config")
    def test_build_services_calls_base_services_factory(
        self,
        mock_load_config,
        mock_data_source_create,
        mock_base_services,
        mock_settings,
        mock_logger,
        mock_pipeline_config,
        mock_services,
    ):
        """Test build_services uses BaseServicesFactory."""
        from bioetl.composition.factories.pipeline_factories import (
            pubchem_compound_factory,
        )

        mock_load_config.return_value = mock_pipeline_config
        mock_base_services.create_common_services.return_value = mock_services
        mock_data_source = MagicMock()
        mock_data_source_create.return_value = mock_data_source

        pubchem_compound_factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        mock_base_services.create_common_services.assert_called_once()

    @patch("bioetl.composition.factories.generic_factory.BaseServicesFactory")
    @patch("bioetl.composition.factories.data_source_registry.DataSourceFactory.create")
    @patch("bioetl.composition.factories.generic_factory.load_pipeline_config")
    def test_build_services_uses_provided_config(
        self,
        mock_load_config,
        mock_data_source_create,
        mock_base_services,
        mock_settings,
        mock_logger,
        mock_pipeline_config,
        mock_services,
    ):
        """Test build_services uses provided configuration."""
        from bioetl.composition.factories.pipeline_factories import (
            pubchem_compound_factory,
        )

        mock_base_services.create_common_services.return_value = mock_services
        mock_data_source = MagicMock()
        mock_data_source_create.return_value = mock_data_source

        pubchem_compound_factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
            config=mock_pipeline_config,
        )

        # Should NOT call load_pipeline_config when config is provided
        mock_load_config.assert_not_called()


# UniProtProteinPipelineFactory tests are covered in tests/unit/pipelines/test_uniprot.py
