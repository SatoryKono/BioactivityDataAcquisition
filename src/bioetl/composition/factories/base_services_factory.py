"""Base factory for creating PipelineServices."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.composition.factories.clients import (
    create_redis_client,
    get_aws_credentials,
)
from bioetl.composition.factories.storage_factory import StorageContext, StorageFactory
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.observability.noop_tracing import NoOpTracing
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger

    from bioetl.domain.ports import (
        CheckpointPort,
        DataSourcePort,
        LockPort,
        MetricsPort,
        QuarantinePort,
        TracingPort,
    )
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class DataSourceFactory(Protocol):
    """Protocol for data source creation."""

    def create(self, settings: Settings, logger: BoundLogger) -> DataSourcePort: ...


class BaseServicesFactory:
    """Reusable factory for common services."""

    @classmethod
    def create_common_services(
        cls,
        settings: Settings,
        logger: BoundLogger,
        data_source: DataSourcePort,
        pipeline_config: PipelineYamlConfig,
    ) -> PipelineServices:
        """Create services with injected data source."""
        storage_ctx = StorageFactory.create(settings, pipeline_config, logger)

        lock = cls._create_lock(settings, logger)
        checkpoint = cls._create_checkpoint(settings, storage_ctx)
        quarantine = cls._create_quarantine(settings, storage_ctx)
        metrics = cls._create_metrics(settings)
        tracing = cls._create_tracing(settings)

        return PipelineServices(
            data_source=data_source,
            storage=storage_ctx.adapter,
            lock=lock,
            checkpoint=checkpoint,
            quarantine=quarantine,
            metrics=metrics,
            tracing=tracing,
            logger=logger,
        )

    @staticmethod
    def _create_lock(settings: Settings, _logger: BoundLogger) -> LockPort:
        if settings.env == "prod":
            return RedisDistributedLock(create_redis_client(settings))
        return MemoryLock()

    @staticmethod
    def _create_checkpoint(
        settings: Settings, storage_ctx: StorageContext
    ) -> CheckpointPort:
        is_local_run = settings.env != "prod" and not settings.aws.endpoint_url
        access_key, secret_key = get_aws_credentials(settings)

        return S3Checkpoint(
            bucket=storage_ctx.checkpoints_path,
            endpoint_url=settings.aws.endpoint_url if not is_local_run else None,
            access_key=access_key,
            secret_key=secret_key,
        )

    @staticmethod
    def _create_quarantine(
        settings: Settings, storage_ctx: StorageContext
    ) -> QuarantinePort:
        is_local_run = settings.env != "prod" and not settings.aws.endpoint_url
        storage_options = settings.storage_options if not is_local_run else None

        return UnifiedQuarantine(
            base_path=f"{storage_ctx.silver_path}/common/quarantine",
            storage_options=storage_options,
        )

    @staticmethod
    def _create_metrics(settings: Settings) -> MetricsPort:
        if getattr(settings, "metrics", None) and settings.metrics.enabled:
            return PrometheusMetrics()
        return NoOpMetrics()

    @staticmethod
    def _create_tracing(_settings: Settings) -> TracingPort:
        # Placeholder for real OTel implementation
        return NoOpTracing()
