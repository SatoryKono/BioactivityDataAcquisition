"""Unit tests for pipeline factories.

Tests creation of services for all pipelines:
- PubChemCompoundPipelineFactory
- UniProtProteinPipelineFactory
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
    config.source = {"api": {"rate_limit": 5.0, "base_url": "https://api.example.com"}}
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
# PubChemCompoundPipelineFactory Tests
# =============================================================================


@pytest.mark.unit
class TestPubChemCompoundPipelineFactory:
    """Tests for PubChemCompoundPipelineFactory."""

    @patch("bioetl.composition.factories.base_pipeline_factory.BaseServicesFactory")
    @patch("bioetl.infrastructure.factories.data_sources.DataSourceFactory.create")
    @patch("bioetl.composition.factories.base_pipeline_factory.load_pipeline_config")
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
        """Test build_services creates data source via DataSourceFactory."""
        from bioetl.composition.factories.pubchem_compound import (
            PubChemCompoundPipelineFactory,
        )

        mock_load_config.return_value = mock_pipeline_config
        mock_base_services.create_common_services.return_value = mock_services
        mock_data_source = MagicMock()
        mock_data_source_create.return_value = mock_data_source

        services = PubChemCompoundPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services is not None
        mock_data_source_create.assert_called_once_with(
            "pubchem",
            http_client=None,
            rate=5.0,
            strict_error_handling=False,
        )

    @patch("bioetl.composition.factories.base_pipeline_factory.BaseServicesFactory")
    @patch("bioetl.infrastructure.factories.data_sources.DataSourceFactory.create")
    @patch("bioetl.composition.factories.base_pipeline_factory.load_pipeline_config")
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
        from bioetl.composition.factories.pubchem_compound import (
            PubChemCompoundPipelineFactory,
        )

        mock_load_config.return_value = mock_pipeline_config
        mock_base_services.create_common_services.return_value = mock_services
        mock_data_source = MagicMock()
        mock_data_source_create.return_value = mock_data_source

        PubChemCompoundPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        mock_base_services.create_common_services.assert_called_once_with(
            settings=mock_settings,
            logger=mock_logger,
            data_source=mock_data_source,
            pipeline_config=mock_pipeline_config,
        )

    @patch("bioetl.composition.factories.base_pipeline_factory.BaseServicesFactory")
    @patch("bioetl.infrastructure.factories.data_sources.DataSourceFactory.create")
    @patch("bioetl.composition.factories.base_pipeline_factory.load_pipeline_config")
    def test_build_services_uses_default_rate_limit(
        self,
        mock_load_config,
        mock_data_source_create,
        mock_base_services,
        mock_settings,
        mock_logger,
        mock_services,
    ):
        """Test build_services uses default rate_limit."""
        from bioetl.composition.factories.pubchem_compound import (
            PubChemCompoundPipelineFactory,
        )

        config = MagicMock()
        config.source = {"api": {}}  # No rate_limit
        mock_load_config.return_value = config
        mock_base_services.create_common_services.return_value = mock_services

        PubChemCompoundPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        mock_data_source_create.assert_called_once_with(
            "pubchem",
            http_client=None,
            rate=5.0,  # Default rate
            strict_error_handling=False,
        )

    @patch("bioetl.composition.factories.base_pipeline_factory.BaseServicesFactory")
    @patch("bioetl.infrastructure.factories.data_sources.DataSourceFactory.create")
    @patch("bioetl.composition.factories.base_pipeline_factory.load_pipeline_config")
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
        from bioetl.composition.factories.pubchem_compound import (
            PubChemCompoundPipelineFactory,
        )

        mock_base_services.create_common_services.return_value = mock_services

        PubChemCompoundPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
            config=mock_pipeline_config,
        )

        # Should NOT call load_pipeline_config when config is provided
        mock_load_config.assert_not_called()

    @patch("bioetl.composition.factories.base_pipeline_factory.yaml_config_to_domain")
    @patch("bioetl.composition.factories.base_pipeline_factory.load_pipeline_config")
    @patch("bioetl.composition.factories.base_pipeline_factory.BaseServicesFactory")
    @patch("bioetl.infrastructure.factories.data_sources.DataSourceFactory.create")
    def test_create_with_services(
        self,
        mock_data_source_create,
        mock_base_services,
        mock_load_config,
        mock_yaml_to_domain,
        mock_settings,
        mock_logger,
        mock_pipeline_config,
        mock_services,
    ):
        """Test create_with_services creates pipeline."""
        from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
        from bioetl.composition.factories.pubchem_compound import (
            PubChemCompoundPipelineFactory,
        )

        mock_load_config.return_value = mock_pipeline_config
        mock_base_services.create_common_services.return_value = mock_services
        mock_domain_config = MagicMock()
        mock_yaml_to_domain.return_value = mock_domain_config

        # Save and patch pipeline_class on the factory to use our mock
        original_class = PubChemCompoundPipelineFactory.pipeline_class
        mock_pipeline_class = MagicMock()
        PubChemCompoundPipelineFactory.pipeline_class = mock_pipeline_class

        try:
            runtime = PipelineRuntimeConfig(run_type=RunType.INCREMENTAL)
            PubChemCompoundPipelineFactory.create_with_services(
                runtime=runtime,
                settings=mock_settings,
                logger=mock_logger,
            )

            mock_pipeline_class.create.assert_called_once_with(
                runtime=runtime,
                services=mock_services,
                config=mock_domain_config,
            )
        finally:
            # Restore original class
            PubChemCompoundPipelineFactory.pipeline_class = original_class


# UniProtProteinPipelineFactory tests are covered in tests/unit/pipelines/test_uniprot.py
