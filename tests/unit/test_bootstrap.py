"""Unit tests for bootstrap module."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.domain.types import RunType
from bioetl.interfaces.orchestration.runner import PipelineRunner


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.env = "staging"
    settings.aws.endpoint_url = None
    settings.aws.region = "us-east-1"
    settings.aws.access_key_id = None
    settings.aws.secret_access_key = None
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


@pytest.mark.unit
class TestBootstrapLogger:
    """Tests for bootstrap_logger function."""

    def test_bootstrap_logger_creates_logger(self):
        """Test that bootstrap_logger creates a logger."""
        from bioetl.interfaces.bootstrap import bootstrap_logger

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

    @patch("bioetl.interfaces.bootstrap.get_settings")
    @patch("bioetl.interfaces.bootstrap.bootstrap_logger")
    def test_bootstrap_pipeline_unknown_pipeline_raises(
        self, mock_bootstrap_logger, mock_get_settings, mock_settings, mock_logger
    ):
        """Test that unknown pipeline name raises ValueError."""
        from bioetl.interfaces.bootstrap import bootstrap_pipeline

        mock_get_settings.return_value = mock_settings
        mock_bootstrap_logger.return_value = mock_logger

        # Now raises "Configuration file not found" because load_pipeline_config is called first
        with pytest.raises(ValueError, match="Configuration file not found"):
            bootstrap_pipeline(
                pipeline_name="unknown_pipeline",
                run_id=uuid4(),
                run_type=RunType.INCREMENTAL,
                resume=False,
                limit=None,
            )

    @patch("bioetl.interfaces.bootstrap.get_settings")
    @patch("bioetl.interfaces.bootstrap.ChEMBLActivityPipelineFactory")
    def test_bootstrap_pipeline_chembl_activity(
        self, mock_factory, mock_get_settings, mock_settings, mock_logger
    ):
        """Test bootstrap_pipeline creates chembl_activity pipeline."""
        from bioetl.interfaces.bootstrap import bootstrap_pipeline

        mock_get_settings.return_value = mock_settings
        mock_pipeline = MagicMock()
        mock_factory.create_with_services.return_value = mock_pipeline

        with patch(
            "bioetl.interfaces.bootstrap.bootstrap_logger", return_value=mock_logger
        ):
            result = bootstrap_pipeline(
                pipeline_name="chembl_activity",
                run_id=uuid4(),
                run_type=RunType.INCREMENTAL,
                resume=False,
                limit=100,
            )

        assert isinstance(result, PipelineRunner)
        assert result.pipeline == mock_pipeline
        mock_factory.create_with_services.assert_called_once()


@pytest.mark.unit
class TestChEMBLActivityPipelineFactory:
    """Tests for ChEMBLActivityPipelineFactory."""

    @patch("bioetl.infrastructure.factories.base_services_factory.BaseServicesFactory.create_common_services")
    @patch("bioetl.interfaces.factories.chembl_activity.DataSourceFactory")
    @patch("bioetl.interfaces.factories.chembl_activity.UnifiedHTTPClient")
    @patch("bioetl.interfaces.factories.chembl_activity.load_pipeline_config")
    def test_build_services_local_run(
        self,
        mock_load_config,
        mock_http,
        mock_datasource_factory,
        mock_create_common_services,
        mock_settings,
        mock_logger,
    ):
        """Test build_services delegates to create_common_services."""
        from bioetl.interfaces.factories.chembl_activity import (
            ChEMBLActivityPipelineFactory,
        )

        mock_settings.env = "dev"
        mock_load_config.return_value = MagicMock()
        mock_services = MagicMock()
        mock_create_common_services.return_value = mock_services

        services = ChEMBLActivityPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services == mock_services
        mock_create_common_services.assert_called_once()
        # Verify call args include what we expect
        call_kwargs = mock_create_common_services.call_args.kwargs
        assert call_kwargs["settings"] == mock_settings
        assert call_kwargs["logger"] == mock_logger
        assert "data_source" in call_kwargs

    # NOTE: The tests 'test_build_services_prod_uses_redis_lock' and 'test_build_services_with_metrics_enabled'
    # were testing BaseServicesFactory logic which is now abstracted away from this factory.
    # Since we only test that create_common_services is called, we don't need to duplicate those tests here.
    # They should be (and likely are) covered in TestBaseServicesFactory.

    @patch(
        "bioetl.interfaces.factories.chembl_activity.ChEMBLActivityPipelineFactory.build_services"
    )
    @patch(
        "bioetl.interfaces.factories.chembl_activity.ChEMBLActivityPipeline",
        create=True,
    )
    def test_create_with_services(
        self,
        mock_pipeline_class,
        mock_build_services,
        mock_settings,
        mock_logger,
    ):
        """Test create_with_services creates pipeline."""
        from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
        from bioetl.interfaces.factories.chembl_activity import (
            ChEMBLActivityPipelineFactory,
        )
        from bioetl.domain.types import RunType

        mock_services = MagicMock()
        mock_build_services.return_value = mock_services

        runtime = PipelineRuntimeConfig(run_type=RunType.INCREMENTAL)
        ChEMBLActivityPipelineFactory.create_with_services(
            runtime=runtime,
            settings=mock_settings,
            logger=mock_logger,
        )

        mock_build_services.assert_called_once()
        mock_pipeline_class.create.assert_called_once()
