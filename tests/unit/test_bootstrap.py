"""Unit tests for bootstrap module."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.application.core.runner import PipelineRunner
from bioetl.domain.context import PipelineRunContext
from bioetl.domain.types import RunType


@pytest.fixture
def mock_settings():
    """Create mock settings."""
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
    return logger


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


@pytest.fixture
def mock_pipeline_config():
    """Create mock pipeline config."""
    config = MagicMock()
    config.source = {"api": {"rate_limit": 10.0}}
    return config


@pytest.mark.unit
class TestBootstrapLogger:
    """Tests for bootstrap_logger function."""

    def test_bootstrap_logger_creates_logger(self):
        """Test that bootstrap_logger creates a logger."""
        from bioetl.composition.bootstrap import bootstrap_logger

        run_id = uuid4()
        logger = bootstrap_logger(
            pipeline="test_pipeline",
            run_id=run_id,
            log_level="INFO",
        )

        assert logger is not None


@pytest.mark.unit
class TestBootstrapPipeline:
    """Tests for bootstrap_pipeline function."""

    @patch("bioetl.composition.bootstrap.get_settings")
    @patch("bioetl.composition.bootstrap.bootstrap_logger")
    def test_bootstrap_pipeline_unknown_pipeline_raises(
        self, mock_bootstrap_logger, mock_get_settings, mock_settings, mock_logger
    ):
        """Test that unknown pipeline name raises ValueError."""
        from bioetl.composition.bootstrap import bootstrap_pipeline

        mock_get_settings.return_value = mock_settings
        mock_bootstrap_logger.return_value = mock_logger

        # Now raises "Configuration file not found" because load_pipeline_config is called first
        ctx = PipelineRunContext(
            pipeline_name="unknown_pipeline",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            resume=False,
            limit=None,
        )
        with pytest.raises(ValueError, match="Configuration file not found"):
            bootstrap_pipeline(ctx)

    @patch("bioetl.composition.bootstrap.PipelineRegistry")
    @patch("bioetl.composition.bootstrap.FilterConfigBuilder")
    @patch("bioetl.composition.bootstrap.load_pipeline_config")
    @patch("bioetl.composition.bootstrap.start_metrics_server")
    @patch("bioetl.composition.bootstrap.bootstrap_tracer")
    @patch("bioetl.composition.bootstrap.bootstrap_logger")
    @patch("bioetl.composition.bootstrap.get_settings")
    def test_bootstrap_pipeline_metrics_server_failure_non_blocking(
        self,
        mock_get_settings: MagicMock,
        mock_bootstrap_logger: MagicMock,
        mock_bootstrap_tracer: MagicMock,
        mock_start_metrics: MagicMock,
        mock_load_config: MagicMock,
        mock_filter_builder: MagicMock,
        mock_registry: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test that metrics server failure doesn't block pipeline bootstrap."""
        from bioetl.composition.bootstrap import bootstrap_pipeline

        # Create proper mock settings with required attributes
        test_settings = MagicMock()
        test_settings.metrics_port = 8000
        test_settings.pipeline = MagicMock()
        test_settings.pipeline.heartbeat_interval = 30

        mock_get_settings.return_value = test_settings
        mock_bootstrap_logger.return_value = mock_logger
        mock_bootstrap_tracer.return_value = MagicMock()
        mock_filter_builder.build.return_value = None

        # Simulate metrics server failure
        mock_start_metrics.side_effect = Exception("Port already in use")

        # Setup pipeline registry mock
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config
        mock_factory = MagicMock()
        mock_runner = MagicMock()
        mock_factory.create_runner.return_value = mock_runner
        mock_registry.get.return_value.factory = mock_factory

        ctx = PipelineRunContext(
            pipeline_name="chembl_activity",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            resume=False,
            limit=None,
        )

        # Should not raise, should return runner despite metrics failure
        result = bootstrap_pipeline(ctx)

        assert result is mock_runner
        mock_start_metrics.assert_called_once_with(test_settings.metrics_port)
        mock_logger.warning.assert_called_with(
            "failed_to_start_metrics_server", error="Port already in use"
        )

    @pytest.mark.skip(
        reason="Requires full integration setup - covered by integration tests"
    )
    @patch("bioetl.composition.bootstrap.get_settings")
    @patch("bioetl.composition.bootstrap.PipelineRegistry")
    def test_bootstrap_pipeline_chembl_activity(
        self, mock_registry, mock_get_settings, mock_settings, mock_logger
    ):
        """Test bootstrap_pipeline creates chembl_activity pipeline."""
        from bioetl.composition.bootstrap import bootstrap_pipeline

        mock_get_settings.return_value = mock_settings
        mock_pipeline = MagicMock()
        mock_factory = MagicMock()
        mock_factory.create_with_services.return_value = mock_pipeline
        mock_registry.get.return_value.factory = mock_factory

        with patch(
            "bioetl.composition.bootstrap.bootstrap_logger", return_value=mock_logger
        ):
            ctx = PipelineRunContext(
                pipeline_name="chembl_activity",
                run_id=uuid4(),
                run_type=RunType.INCREMENTAL,
                resume=False,
                limit=100,
            )
            result = bootstrap_pipeline(ctx)

        assert isinstance(result, PipelineRunner)
        mock_factory.create_with_services.assert_called_once()


@pytest.mark.unit
class TestChemblActivityFactory:
    """Tests for chembl_activity_factory (GenericPipelineFactory instance)."""

    @patch("bioetl.composition.factories.generic_factory.BaseServicesFactory")
    @patch("bioetl.composition.factories.data_source_registry.HttpClientFactory")
    @patch("bioetl.composition.factories.data_source_registry.DataSourceFactory.create")
    @patch("bioetl.composition.factories.generic_factory.load_pipeline_config")
    def test_build_services_creates_data_source(
        self,
        mock_load_config,
        mock_data_source_create,
        mock_http_client_factory,
        mock_base_services,
        mock_settings,
        mock_logger,
        mock_services,
        mock_pipeline_config,
    ):
        """Test build_services creates data source through DataSourceRegistry."""
        from bioetl.composition.factories.pipeline_factories import (
            chembl_activity_factory,
        )

        mock_load_config.return_value = mock_pipeline_config
        mock_base_services.create_common_services.return_value = mock_services
        mock_data_source = MagicMock()
        mock_data_source_create.return_value = mock_data_source
        mock_http_client = MagicMock()
        mock_http_client_factory.create_for_provider.return_value = mock_http_client

        services = chembl_activity_factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services is not None
        mock_data_source_create.assert_called_once()

    @patch("bioetl.composition.factories.generic_factory.BaseServicesFactory")
    @patch("bioetl.composition.factories.data_source_registry.HttpClientFactory")
    @patch("bioetl.composition.factories.data_source_registry.DataSourceFactory.create")
    @patch("bioetl.composition.factories.generic_factory.load_pipeline_config")
    def test_build_services_calls_base_services_factory(
        self,
        mock_load_config,
        mock_data_source_create,
        mock_http_client_factory,
        mock_base_services,
        mock_settings,
        mock_logger,
        mock_services,
        mock_pipeline_config,
    ):
        """Test build_services uses BaseServicesFactory."""
        from bioetl.composition.factories.pipeline_factories import (
            chembl_activity_factory,
        )

        mock_load_config.return_value = mock_pipeline_config
        mock_base_services.create_common_services.return_value = mock_services
        mock_data_source = MagicMock()
        mock_data_source_create.return_value = mock_data_source

        chembl_activity_factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        mock_base_services.create_common_services.assert_called_once()

    @patch("bioetl.composition.factories.generic_factory.BaseServicesFactory")
    @patch("bioetl.composition.factories.data_source_registry.HttpClientFactory")
    @patch("bioetl.composition.factories.data_source_registry.DataSourceFactory.create")
    @patch("bioetl.composition.factories.generic_factory.load_pipeline_config")
    def test_build_services_uses_provided_config(
        self,
        mock_load_config,
        mock_data_source_create,
        mock_http_client_factory,
        mock_base_services,
        mock_settings,
        mock_logger,
        mock_services,
        mock_pipeline_config,
    ):
        """Test build_services uses provided config."""
        from bioetl.composition.factories.pipeline_factories import (
            chembl_activity_factory,
        )

        mock_base_services.create_common_services.return_value = mock_services
        mock_data_source = MagicMock()
        mock_data_source_create.return_value = mock_data_source

        chembl_activity_factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
            config=mock_pipeline_config,
        )

        # Should NOT call load_pipeline_config when config is provided
        mock_load_config.assert_not_called()

    @patch("bioetl.composition.factories.generic_factory.yaml_config_to_domain")
    @patch("bioetl.composition.factories.generic_factory.load_pipeline_config")
    @patch("bioetl.composition.factories.generic_factory.BaseServicesFactory")
    @patch("bioetl.composition.factories.data_source_registry.HttpClientFactory")
    @patch("bioetl.composition.factories.data_source_registry.DataSourceFactory.create")
    def test_create_with_services(
        self,
        mock_data_source_create,
        mock_http_client_factory,
        mock_base_services,
        mock_load_config,
        mock_yaml_to_domain,
        mock_settings,
        mock_logger,
        mock_services,
        mock_pipeline_config,
    ):
        """Test create_with_services creates pipeline with run_id."""
        from bioetl.composition.factories.pipeline_factories import (
            chembl_activity_factory,
        )
        from bioetl.domain.config import RuntimeConfig

        mock_load_config.return_value = mock_pipeline_config
        mock_base_services.create_common_services.return_value = mock_services
        mock_domain_config = MagicMock()
        mock_yaml_to_domain.return_value = mock_domain_config
        mock_data_source = MagicMock()
        mock_data_source_create.return_value = mock_data_source

        # Create a mock pipeline class
        mock_pipeline_class = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline_class.create.return_value = mock_pipeline

        # Temporarily replace pipeline_class
        original_class = chembl_activity_factory.pipeline_class
        chembl_activity_factory.pipeline_class = mock_pipeline_class

        try:
            runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)
            run_id = uuid4()
            result = chembl_activity_factory.create_with_services(
                run_id=run_id,
                runtime=runtime,
                settings=mock_settings,
                logger=mock_logger,
            )

            # Verify run_id is passed to pipeline.create()
            mock_pipeline_class.create.assert_called_once_with(
                run_id=run_id,
                runtime=runtime,
                services=mock_services,
                config=mock_domain_config,
            )
            assert result is mock_pipeline
        finally:
            # Restore original class
            chembl_activity_factory.pipeline_class = original_class
