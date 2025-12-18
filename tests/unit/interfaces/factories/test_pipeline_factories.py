"""Unit tests for pipeline factories.

Тестирует создание сервисов для всех пайплайнов:
- PubChemCompoundPipelineFactory
- UniProtProteinPipelineFactory
"""

from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.types import RunType


@pytest.fixture
def mock_settings():
    """Создаёт mock настроек приложения."""
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
    """Создаёт mock логгера."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def mock_storage_ctx():
    """Создаёт mock контекста хранилища."""
    ctx = MagicMock()
    ctx.checkpoints_path = "checkpoints"
    ctx.silver_path = "silver"
    ctx.adapter = MagicMock()
    return ctx


@pytest.fixture
def mock_pipeline_config():
    """Создаёт mock конфигурации пайплайна."""
    config = MagicMock()
    config.source = {"api": {"rate_limit": 5.0, "base_url": "https://api.example.com"}}
    return config


# =============================================================================
# PubChemCompoundPipelineFactory Tests
# =============================================================================


@pytest.mark.unit
class TestPubChemCompoundPipelineFactory:
    """Тесты для PubChemCompoundPipelineFactory."""

    @patch("bioetl.interfaces.factories.pubchem_compound.get_aws_credentials")
    @patch("bioetl.interfaces.factories.pubchem_compound.PubChemClient")
    @patch("bioetl.interfaces.factories.pubchem_compound.StorageFactory")
    @patch("bioetl.interfaces.factories.pubchem_compound.S3Checkpoint")
    @patch("bioetl.interfaces.factories.pubchem_compound.UnifiedQuarantine")
    @patch("bioetl.interfaces.factories.pubchem_compound.load_pipeline_config")
    def test_build_services_local_run(
        self,
        mock_load_config,
        mock_quarantine,
        mock_checkpoint,
        mock_storage_factory,
        mock_pubchem_client,
        mock_aws_creds,
        mock_settings,
        mock_logger,
        mock_storage_ctx,
        mock_pipeline_config,
    ):
        """Тест build_services для локального запуска."""
        from bioetl.interfaces.factories.pubchem_compound import (
            PubChemCompoundPipelineFactory,
        )

        mock_aws_creds.return_value = (None, None)
        mock_settings.env = "dev"
        mock_settings.aws.endpoint_url = None
        mock_load_config.return_value = mock_pipeline_config
        mock_storage_factory.create.return_value = mock_storage_ctx

        services = PubChemCompoundPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services is not None
        assert services.data_source is not None
        assert services.storage is not None
        assert services.lock is not None
        mock_pubchem_client.assert_called_once()

    @patch("bioetl.interfaces.factories.pubchem_compound.get_aws_credentials")
    @patch("bioetl.interfaces.factories.pubchem_compound.create_redis_client")
    @patch("bioetl.interfaces.factories.pubchem_compound.RedisDistributedLock")
    @patch("bioetl.interfaces.factories.pubchem_compound.PubChemClient")
    @patch("bioetl.interfaces.factories.pubchem_compound.StorageFactory")
    @patch("bioetl.interfaces.factories.pubchem_compound.S3Checkpoint")
    @patch("bioetl.interfaces.factories.pubchem_compound.UnifiedQuarantine")
    @patch("bioetl.interfaces.factories.pubchem_compound.load_pipeline_config")
    def test_build_services_prod_uses_redis_lock(
        self,
        mock_load_config,
        mock_quarantine,
        mock_checkpoint,
        mock_storage_factory,
        mock_pubchem_client,
        mock_redis_lock,
        mock_redis_client,
        mock_aws_creds,
        mock_settings,
        mock_logger,
        mock_storage_ctx,
        mock_pipeline_config,
    ):
        """Тест build_services использует Redis lock в production."""
        from bioetl.interfaces.factories.pubchem_compound import (
            PubChemCompoundPipelineFactory,
        )

        mock_aws_creds.return_value = ("key", "secret")
        mock_settings.env = "prod"
        mock_settings.aws.endpoint_url = "http://s3.example.com"
        mock_load_config.return_value = mock_pipeline_config
        mock_storage_factory.create.return_value = mock_storage_ctx

        services = PubChemCompoundPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services is not None
        mock_redis_client.assert_called_once()
        mock_redis_lock.assert_called_once()

    @patch("bioetl.interfaces.factories.pubchem_compound.get_aws_credentials")
    @patch("bioetl.interfaces.factories.pubchem_compound.PubChemClient")
    @patch("bioetl.interfaces.factories.pubchem_compound.StorageFactory")
    @patch("bioetl.interfaces.factories.pubchem_compound.S3Checkpoint")
    @patch("bioetl.interfaces.factories.pubchem_compound.UnifiedQuarantine")
    @patch("bioetl.interfaces.factories.pubchem_compound.PrometheusMetrics")
    @patch("bioetl.interfaces.factories.pubchem_compound.load_pipeline_config")
    def test_build_services_with_metrics_enabled(
        self,
        mock_load_config,
        mock_prometheus,
        mock_quarantine,
        mock_checkpoint,
        mock_storage_factory,
        mock_pubchem_client,
        mock_aws_creds,
        mock_settings,
        mock_logger,
        mock_storage_ctx,
        mock_pipeline_config,
    ):
        """Тест build_services использует PrometheusMetrics когда включено."""
        from bioetl.interfaces.factories.pubchem_compound import (
            PubChemCompoundPipelineFactory,
        )

        mock_aws_creds.return_value = (None, None)
        mock_settings.env = "staging"
        mock_settings.metrics = MagicMock()
        mock_settings.metrics.enabled = True
        mock_load_config.return_value = mock_pipeline_config
        mock_storage_factory.create.return_value = mock_storage_ctx

        services = PubChemCompoundPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services is not None
        mock_prometheus.assert_called_once()

    @patch("bioetl.interfaces.factories.pubchem_compound.get_aws_credentials")
    @patch("bioetl.interfaces.factories.pubchem_compound.PubChemClient")
    @patch("bioetl.interfaces.factories.pubchem_compound.StorageFactory")
    @patch("bioetl.interfaces.factories.pubchem_compound.S3Checkpoint")
    @patch("bioetl.interfaces.factories.pubchem_compound.UnifiedQuarantine")
    @patch("bioetl.interfaces.factories.pubchem_compound.load_pipeline_config")
    def test_build_services_uses_config_rate_limit(
        self,
        mock_load_config,
        mock_quarantine,
        mock_checkpoint,
        mock_storage_factory,
        mock_pubchem_client,
        mock_aws_creds,
        mock_settings,
        mock_logger,
        mock_storage_ctx,
    ):
        """Тест build_services использует rate_limit из конфига."""
        from bioetl.interfaces.factories.pubchem_compound import (
            PubChemCompoundPipelineFactory,
        )

        mock_aws_creds.return_value = (None, None)
        mock_settings.env = "dev"

        config = MagicMock()
        config.source = {"api": {"rate_limit": 3.0}}
        mock_load_config.return_value = config
        mock_storage_factory.create.return_value = mock_storage_ctx

        PubChemCompoundPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        mock_pubchem_client.assert_called_once_with(rate=3.0)

    @patch(
        "bioetl.interfaces.factories.pubchem_compound.PubChemCompoundPipelineFactory.build_services"
    )
    @patch(
        "bioetl.interfaces.factories.pubchem_compound.PubChemCompoundPipeline",
        create=True,
    )
    @patch("bioetl.interfaces.factories.pubchem_compound.load_pipeline_config")
    @patch("bioetl.interfaces.factories.pubchem_compound.get_pipeline_config")
    def test_create_with_services(
        self,
        mock_get_config,
        mock_load_config,
        mock_pipeline_class,
        mock_build_services,
        mock_settings,
        mock_logger,
    ):
        """Тест create_with_services создаёт пайплайн."""
        from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
        from bioetl.interfaces.factories.pubchem_compound import (
            PubChemCompoundPipelineFactory,
        )

        mock_services = MagicMock()
        mock_build_services.return_value = mock_services
        mock_load_config.return_value = MagicMock()
        mock_get_config.return_value = MagicMock()

        runtime = PipelineRuntimeConfig(run_type=RunType.INCREMENTAL)
        PubChemCompoundPipelineFactory.create_with_services(
            runtime=runtime,
            settings=mock_settings,
            logger=mock_logger,
        )

        mock_build_services.assert_called_once()
        mock_pipeline_class.create.assert_called_once()


# =============================================================================
# UniProtProteinPipelineFactory Tests
# =============================================================================


@pytest.mark.unit
class TestUniProtProteinPipelineFactory:
    """Тесты для UniProtProteinPipelineFactory."""

    @patch("bioetl.interfaces.factories.uniprot_protein.get_aws_credentials")
    @patch("bioetl.interfaces.factories.uniprot_protein.UniProtClient")
    @patch("bioetl.interfaces.factories.uniprot_protein.StorageFactory")
    @patch("bioetl.interfaces.factories.uniprot_protein.S3Checkpoint")
    @patch("bioetl.interfaces.factories.uniprot_protein.UnifiedQuarantine")
    @patch("bioetl.interfaces.factories.uniprot_protein.load_pipeline_config")
    def test_build_services_local_run(
        self,
        mock_load_config,
        mock_quarantine,
        mock_checkpoint,
        mock_storage_factory,
        mock_uniprot_client,
        mock_aws_creds,
        mock_settings,
        mock_logger,
        mock_storage_ctx,
        mock_pipeline_config,
    ):
        """Тест build_services для локального запуска."""
        from bioetl.interfaces.factories.uniprot_protein import (
            UniProtProteinPipelineFactory,
        )

        mock_aws_creds.return_value = (None, None)
        mock_settings.env = "dev"
        mock_settings.aws.endpoint_url = None
        mock_load_config.return_value = mock_pipeline_config
        mock_storage_factory.create.return_value = mock_storage_ctx

        services = UniProtProteinPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services is not None
        assert services.data_source is not None
        assert services.storage is not None
        assert services.lock is not None
        mock_uniprot_client.assert_called_once()

    @patch("bioetl.interfaces.factories.uniprot_protein.get_aws_credentials")
    @patch("bioetl.interfaces.factories.uniprot_protein.create_redis_client")
    @patch("bioetl.interfaces.factories.uniprot_protein.RedisDistributedLock")
    @patch("bioetl.interfaces.factories.uniprot_protein.UniProtClient")
    @patch("bioetl.interfaces.factories.uniprot_protein.StorageFactory")
    @patch("bioetl.interfaces.factories.uniprot_protein.S3Checkpoint")
    @patch("bioetl.interfaces.factories.uniprot_protein.UnifiedQuarantine")
    @patch("bioetl.interfaces.factories.uniprot_protein.load_pipeline_config")
    def test_build_services_prod_uses_redis_lock(
        self,
        mock_load_config,
        mock_quarantine,
        mock_checkpoint,
        mock_storage_factory,
        mock_uniprot_client,
        mock_redis_lock,
        mock_redis_client,
        mock_aws_creds,
        mock_settings,
        mock_logger,
        mock_storage_ctx,
        mock_pipeline_config,
    ):
        """Тест build_services использует Redis lock в production."""
        from bioetl.interfaces.factories.uniprot_protein import (
            UniProtProteinPipelineFactory,
        )

        mock_aws_creds.return_value = ("key", "secret")
        mock_settings.env = "prod"
        mock_settings.aws.endpoint_url = "http://s3.example.com"
        mock_load_config.return_value = mock_pipeline_config
        mock_storage_factory.create.return_value = mock_storage_ctx

        services = UniProtProteinPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services is not None
        mock_redis_client.assert_called_once()
        mock_redis_lock.assert_called_once()

    @patch("bioetl.interfaces.factories.uniprot_protein.get_aws_credentials")
    @patch("bioetl.interfaces.factories.uniprot_protein.UniProtClient")
    @patch("bioetl.interfaces.factories.uniprot_protein.StorageFactory")
    @patch("bioetl.interfaces.factories.uniprot_protein.S3Checkpoint")
    @patch("bioetl.interfaces.factories.uniprot_protein.UnifiedQuarantine")
    @patch("bioetl.interfaces.factories.uniprot_protein.PrometheusMetrics")
    @patch("bioetl.interfaces.factories.uniprot_protein.load_pipeline_config")
    def test_build_services_with_metrics_enabled(
        self,
        mock_load_config,
        mock_prometheus,
        mock_quarantine,
        mock_checkpoint,
        mock_storage_factory,
        mock_uniprot_client,
        mock_aws_creds,
        mock_settings,
        mock_logger,
        mock_storage_ctx,
        mock_pipeline_config,
    ):
        """Тест build_services использует PrometheusMetrics когда включено."""
        from bioetl.interfaces.factories.uniprot_protein import (
            UniProtProteinPipelineFactory,
        )

        mock_aws_creds.return_value = (None, None)
        mock_settings.env = "staging"
        mock_settings.metrics = MagicMock()
        mock_settings.metrics.enabled = True
        mock_load_config.return_value = mock_pipeline_config
        mock_storage_factory.create.return_value = mock_storage_ctx

        services = UniProtProteinPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services is not None
        mock_prometheus.assert_called_once()

    @patch("bioetl.interfaces.factories.uniprot_protein.get_aws_credentials")
    @patch("bioetl.interfaces.factories.uniprot_protein.UniProtClient")
    @patch("bioetl.interfaces.factories.uniprot_protein.StorageFactory")
    @patch("bioetl.interfaces.factories.uniprot_protein.S3Checkpoint")
    @patch("bioetl.interfaces.factories.uniprot_protein.UnifiedQuarantine")
    @patch("bioetl.interfaces.factories.uniprot_protein.load_pipeline_config")
    def test_build_services_uses_config_parameters(
        self,
        mock_load_config,
        mock_quarantine,
        mock_checkpoint,
        mock_storage_factory,
        mock_uniprot_client,
        mock_aws_creds,
        mock_settings,
        mock_logger,
        mock_storage_ctx,
    ):
        """Тест build_services использует параметры из конфига."""
        from bioetl.interfaces.factories.uniprot_protein import (
            UniProtProteinPipelineFactory,
        )

        mock_aws_creds.return_value = (None, None)
        mock_settings.env = "dev"

        config = MagicMock()
        config.source = {
            "api": {
                "rate_limit": 15.0,
                "base_url": "https://custom.uniprot.org"
            }
        }
        mock_load_config.return_value = config
        mock_storage_factory.create.return_value = mock_storage_ctx

        UniProtProteinPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        mock_uniprot_client.assert_called_once_with(
            rate=15.0,
            base_url="https://custom.uniprot.org"
        )

    @patch("bioetl.interfaces.factories.uniprot_protein.get_aws_credentials")
    @patch("bioetl.interfaces.factories.uniprot_protein.UniProtClient")
    @patch("bioetl.interfaces.factories.uniprot_protein.StorageFactory")
    @patch("bioetl.interfaces.factories.uniprot_protein.S3Checkpoint")
    @patch("bioetl.interfaces.factories.uniprot_protein.UnifiedQuarantine")
    @patch("bioetl.interfaces.factories.uniprot_protein.load_pipeline_config")
    def test_build_services_uses_default_base_url(
        self,
        mock_load_config,
        mock_quarantine,
        mock_checkpoint,
        mock_storage_factory,
        mock_uniprot_client,
        mock_aws_creds,
        mock_settings,
        mock_logger,
        mock_storage_ctx,
    ):
        """Тест build_services использует дефолтный base_url."""
        from bioetl.interfaces.factories.uniprot_protein import (
            UniProtProteinPipelineFactory,
        )

        mock_aws_creds.return_value = (None, None)
        mock_settings.env = "dev"

        config = MagicMock()
        config.source = {"api": {}}  # No rate_limit or base_url
        mock_load_config.return_value = config
        mock_storage_factory.create.return_value = mock_storage_ctx

        UniProtProteinPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        mock_uniprot_client.assert_called_once_with(
            rate=10.0,
            base_url="https://rest.uniprot.org"
        )

    @patch(
        "bioetl.interfaces.factories.uniprot_protein.UniProtProteinPipelineFactory.build_services"
    )
    @patch(
        "bioetl.interfaces.factories.uniprot_protein.UniProtProteinPipeline",
        create=True,
    )
    @patch("bioetl.interfaces.factories.uniprot_protein.load_pipeline_config")
    @patch("bioetl.interfaces.factories.uniprot_protein.get_pipeline_config")
    def test_create_with_services(
        self,
        mock_get_config,
        mock_load_config,
        mock_pipeline_class,
        mock_build_services,
        mock_settings,
        mock_logger,
    ):
        """Тест create_with_services создаёт пайплайн."""
        from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
        from bioetl.interfaces.factories.uniprot_protein import (
            UniProtProteinPipelineFactory,
        )

        mock_services = MagicMock()
        mock_build_services.return_value = mock_services
        mock_load_config.return_value = MagicMock()
        mock_get_config.return_value = MagicMock()

        runtime = PipelineRuntimeConfig(run_type=RunType.INCREMENTAL)
        UniProtProteinPipelineFactory.create_with_services(
            runtime=runtime,
            settings=mock_settings,
            logger=mock_logger,
        )

        mock_build_services.assert_called_once()
        mock_pipeline_class.create.assert_called_once()

    @patch("bioetl.interfaces.factories.uniprot_protein.get_aws_credentials")
    @patch("bioetl.interfaces.factories.uniprot_protein.UniProtClient")
    @patch("bioetl.interfaces.factories.uniprot_protein.StorageFactory")
    @patch("bioetl.interfaces.factories.uniprot_protein.S3Checkpoint")
    @patch("bioetl.interfaces.factories.uniprot_protein.UnifiedQuarantine")
    @patch("bioetl.interfaces.factories.uniprot_protein.NoOpMetrics")
    @patch("bioetl.interfaces.factories.uniprot_protein.load_pipeline_config")
    def test_build_services_uses_noop_metrics_when_disabled(
        self,
        mock_load_config,
        mock_noop_metrics,
        mock_quarantine,
        mock_checkpoint,
        mock_storage_factory,
        mock_uniprot_client,
        mock_aws_creds,
        mock_settings,
        mock_logger,
        mock_storage_ctx,
        mock_pipeline_config,
    ):
        """Тест build_services использует NoOpMetrics когда метрики отключены."""
        from bioetl.interfaces.factories.uniprot_protein import (
            UniProtProteinPipelineFactory,
        )

        mock_aws_creds.return_value = (None, None)
        mock_settings.env = "dev"
        mock_settings.metrics = None  # Metrics disabled
        mock_load_config.return_value = mock_pipeline_config
        mock_storage_factory.create.return_value = mock_storage_ctx

        services = UniProtProteinPipelineFactory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services is not None
        mock_noop_metrics.assert_called_once()
