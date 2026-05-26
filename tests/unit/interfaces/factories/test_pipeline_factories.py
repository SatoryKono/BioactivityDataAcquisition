"""Unit tests for pipeline factories.

Tests that pipeline factory instances are properly exported and configured.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


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
    """Create mock PipelineService."""
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

    @pytest.fixture(autouse=True)
    def _restore_factory_state(self):
        """Restore factory state after each test to prevent pollution."""
        from bioetl.composition.factories.pipeline.registry import (
            pubchem_compound_factory,
        )

        # Save original _create_data_source
        original_creator = pubchem_compound_factory._create_data_source
        yield
        # Restore after test
        pubchem_compound_factory._create_data_source = original_creator

    @patch("bioetl.composition.factories.services.factory.BaseServicesFactory")
    @patch("bioetl.composition.factories.services.bundle.load_pipeline_config")
    def test_build_services_creates_data_source__test_pub_chem_compound_factory_interfaces_factories_test_pipeline_factories_93(
        self,
        mock_load_config,
        mock_base_services,
        mock_settings,
        mock_logger,
        mock_pipeline_config,
        mock_services,
    ):
        """Test build_services creates a data source via the stored creator."""
        from bioetl.composition.factories.pipeline.registry import (
            pubchem_compound_factory,
        )

        mock_load_config.return_value = mock_pipeline_config
        mock_base_services.create_common_services.return_value = mock_services

        # Mock the data source creator function stored in the factory
        mock_data_source = MagicMock()
        pubchem_compound_factory._create_data_source = MagicMock(
            return_value=mock_data_source
        )

        services = pubchem_compound_factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services is not None
        # Verify data source creator was called
        pubchem_compound_factory._create_data_source.assert_called_once()

    @patch("bioetl.composition.factories.services.factory.BaseServicesFactory")
    @patch("bioetl.composition.factories.services.bundle.load_pipeline_config")
    def test_build_services_calls_base_services_factory__test_pub_chem_compound_factory_interfaces_factories_test_pipeline_factories_127(
        self,
        mock_load_config,
        mock_base_services,
        mock_settings,
        mock_logger,
        mock_pipeline_config,
        mock_services,
    ):
        """Test build_services uses BaseServicesFactory."""
        from bioetl.composition.factories.pipeline.registry import (
            pubchem_compound_factory,
        )

        mock_load_config.return_value = mock_pipeline_config
        mock_base_services.create_common_services.return_value = mock_services

        # Mock the data source creator
        mock_data_source = MagicMock()
        pubchem_compound_factory._create_data_source = MagicMock(
            return_value=mock_data_source
        )

        pubchem_compound_factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        mock_base_services.create_common_services.assert_called_once()

    @patch("bioetl.composition.factories.services.factory.BaseServicesFactory")
    @patch("bioetl.composition.factories.services.bundle.load_pipeline_config")
    def test_build_services_uses_provided_config__test_pub_chem_compound_factory_interfaces_factories_test_pipeline_factories_159(
        self,
        mock_load_config,
        mock_base_services,
        mock_settings,
        mock_logger,
        mock_pipeline_config,
        mock_services,
    ):
        """Test build_services uses provided configuration."""
        from bioetl.composition.factories.pipeline.registry import (
            pubchem_compound_factory,
        )

        mock_base_services.create_common_services.return_value = mock_services

        # Mock the data source creator
        mock_data_source = MagicMock()
        pubchem_compound_factory._create_data_source = MagicMock(
            return_value=mock_data_source
        )

        pubchem_compound_factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
            config=mock_pipeline_config,
        )

        # Should NOT call load_pipeline_config when config is provided
        mock_load_config.assert_not_called()


# UniProtProteinPipelineFactory tests are covered in tests/unit/pipelines/test_uniprot.py
