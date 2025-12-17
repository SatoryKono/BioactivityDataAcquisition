"""Unit tests for bootstrap module."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.domain.types import RunType


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

    def test_bootstrap_pipeline_unknown_pipeline_raises(self):
        """Test that unknown pipeline name raises ValueError."""
        from bioetl.interfaces.bootstrap import bootstrap_pipeline

        with pytest.raises(ValueError, match="Unknown pipeline name"):
            bootstrap_pipeline(
                pipeline_name="unknown_pipeline",
                run_id=uuid4(),
                run_type=RunType.INCREMENTAL,
                resume=False,
                limit=None,
            )

    @patch("bioetl.interfaces.bootstrap.get_settings")
    @patch("bioetl.interfaces.factories.chembl_activity.ChEMBLActivityPipelineFactory")
    def test_bootstrap_pipeline_chembl_activity(
        self, mock_factory, mock_get_settings, mock_settings, mock_logger
    ):
        """Test bootstrap_pipeline creates chembl_activity pipeline."""
        from bioetl.interfaces.bootstrap import bootstrap_pipeline

        mock_get_settings.return_value = mock_settings
        mock_pipeline = MagicMock()
        mock_factory.create_with_services.return_value = mock_pipeline

        with patch("bioetl.interfaces.bootstrap.bootstrap_logger", return_value=mock_logger):
            result = bootstrap_pipeline(
                pipeline_name="chembl_activity",
                run_id=uuid4(),
                run_type=RunType.INCREMENTAL,
                resume=False,
                limit=100,
            )

        assert result == mock_pipeline
        mock_factory.create_with_services.assert_called_once()


@pytest.mark.unit
class TestChEMBLActivityPipelineFactory:
    """Tests for ChEMBLActivityPipelineFactory."""

    @patch("bioetl.interfaces.factories.chembl_activity.get_aws_credentials")
    @patch("bioetl.interfaces.factories.chembl_activity.UnifiedHTTPClient")
    @patch("bioetl.interfaces.factories.chembl_activity.ChemblAdapter")
    @patch("bioetl.interfaces.factories.chembl_activity.StorageAdapter")
    @patch("bioetl.interfaces.factories.chembl_activity.BronzeWriter")
    @patch("bioetl.interfaces.factories.chembl_activity.DeltaWriter")
    @patch("bioetl.interfaces.factories.chembl_activity.GoldWriter")
    @patch("bioetl.interfaces.factories.chembl_activity.S3Checkpoint")
    @patch("bioetl.interfaces.factories.chembl_activity.UnifiedQuarantine")
    def test_build_services_local_run(
        self,
        mock_quarantine,
        mock_checkpoint,
        mock_gold,
        mock_delta,
        mock_bronze,
        mock_storage,
        mock_chembl,
        mock_http,
        mock_aws_creds,
        mock_settings,
        mock_logger,
    ):
        """Test build_services for local run (no S3 endpoint)."""
        from bioetl.interfaces.factories.chembl_activity import (
            ChEMBLActivityPipelineFactory,
        )

        mock_aws_creds.return_value = (None, None)
        mock_settings.env = "dev"
        mock_settings.aws.endpoint_url = None

        services = ChEMBLActivityPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services is not None
        mock_logger.warning.assert_called()  # MemoryLock warning

    @patch("bioetl.interfaces.factories.chembl_activity.get_aws_credentials")
    @patch("bioetl.interfaces.factories.chembl_activity.create_redis_client")
    @patch("bioetl.interfaces.factories.chembl_activity.RedisDistributedLock")
    @patch("bioetl.interfaces.factories.chembl_activity.UnifiedHTTPClient")
    @patch("bioetl.interfaces.factories.chembl_activity.ChemblAdapter")
    @patch("bioetl.interfaces.factories.chembl_activity.StorageAdapter")
    @patch("bioetl.interfaces.factories.chembl_activity.BronzeWriter")
    @patch("bioetl.interfaces.factories.chembl_activity.DeltaWriter")
    @patch("bioetl.interfaces.factories.chembl_activity.GoldWriter")
    @patch("bioetl.interfaces.factories.chembl_activity.S3Checkpoint")
    @patch("bioetl.interfaces.factories.chembl_activity.UnifiedQuarantine")
    def test_build_services_prod_uses_redis_lock(
        self,
        mock_quarantine,
        mock_checkpoint,
        mock_gold,
        mock_delta,
        mock_bronze,
        mock_storage,
        mock_chembl,
        mock_http,
        mock_redis_lock,
        mock_redis_client,
        mock_aws_creds,
        mock_settings,
        mock_logger,
    ):
        """Test build_services uses Redis lock in production."""
        from bioetl.interfaces.factories.chembl_activity import (
            ChEMBLActivityPipelineFactory,
        )

        mock_aws_creds.return_value = ("key", "secret")
        mock_settings.env = "prod"
        mock_settings.aws.endpoint_url = "http://s3.example.com"

        services = ChEMBLActivityPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services is not None
        mock_redis_client.assert_called_once()
        mock_redis_lock.assert_called_once()
        mock_logger.info.assert_called()

    @patch("bioetl.interfaces.factories.chembl_activity.get_aws_credentials")
    @patch("bioetl.interfaces.factories.chembl_activity.UnifiedHTTPClient")
    @patch("bioetl.interfaces.factories.chembl_activity.ChemblAdapter")
    @patch("bioetl.interfaces.factories.chembl_activity.StorageAdapter")
    @patch("bioetl.interfaces.factories.chembl_activity.BronzeWriter")
    @patch("bioetl.interfaces.factories.chembl_activity.DeltaWriter")
    @patch("bioetl.interfaces.factories.chembl_activity.GoldWriter")
    @patch("bioetl.interfaces.factories.chembl_activity.S3Checkpoint")
    @patch("bioetl.interfaces.factories.chembl_activity.UnifiedQuarantine")
    @patch("bioetl.interfaces.factories.chembl_activity.PrometheusMetrics")
    def test_build_services_with_metrics_enabled(
        self,
        mock_prometheus,
        mock_quarantine,
        mock_checkpoint,
        mock_gold,
        mock_delta,
        mock_bronze,
        mock_storage,
        mock_chembl,
        mock_http,
        mock_aws_creds,
        mock_settings,
        mock_logger,
    ):
        """Test build_services uses PrometheusMetrics when enabled."""
        from bioetl.interfaces.factories.chembl_activity import (
            ChEMBLActivityPipelineFactory,
        )

        mock_aws_creds.return_value = (None, None)
        mock_settings.env = "staging"
        mock_settings.metrics = MagicMock()
        mock_settings.metrics.enabled = True

        services = ChEMBLActivityPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services is not None
        mock_prometheus.assert_called_once()

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
