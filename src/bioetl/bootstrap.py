"""Composition Root for BioETL.

Handles the initialization and wiring of infrastructure components (adapters)
to provide a ready-to-use dependency container for the application layer.

This is the only place where infrastructure imports are allowed to create
concrete implementations of domain ports.

Refactored per ADR-0005 to use PipelineConfig, PipelineRuntimeConfig, PipelineServices.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.pipelines.chembl_activity import CHEMBL_ACTIVITY_CONFIG
from bioetl.config import Settings, get_settings
from bioetl.domain.ports import MetricsPort
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.factories.clients import (
    create_redis_client,
    get_aws_credentials,
)
from bioetl.infrastructure.factories.storage import StorageAdapter
from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock
from bioetl.infrastructure.observability.logging import (
    create_logger as create_infra_logger,
)
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter

if TYPE_CHECKING:
    from uuid import UUID

    import redis.asyncio as aioredis
    import structlog

    from bioetl.application.pipelines.chembl_activity import ChEMBLActivityPipeline
    from bioetl.domain.ports import CheckpointPort, LockPort, QuarantinePort
    from bioetl.domain.types import RunType


def bootstrap_logger(
    pipeline: str, run_id: UUID, log_level: str = "INFO"
) -> structlog.BoundLogger:
    """Create a logger for the application layer (e.g., CLI)."""
    return create_infra_logger(
        pipeline=pipeline, run_id=run_id, log_level=log_level, json_format=True
    )


@dataclass(frozen=True)
class ServiceContainer:
    """Container for initialized infrastructure services.

    NOTE: Consider using PipelineServices instead for new code.
    This class is kept for backward compatibility.
    """

    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    lock: LockPort
    metrics: MetricsPort
    redis_client: aioredis.Redis


def bootstrap() -> ServiceContainer:
    """Initialize all infrastructure services.

    Returns:
        ServiceContainer with ready-to-use adapters.
    """
    settings = get_settings()
    aws_config = settings.aws
    s3_config = settings.s3
    storage_options = settings.storage_options

    # Initialize Redis Client using the factory
    redis_client = create_redis_client(settings)

    # Initialize Adapters
    access_key, secret_key = get_aws_credentials(settings)
    checkpoint = S3Checkpoint(
        bucket=s3_config.bucket_checkpoints,
        endpoint_url=aws_config.endpoint_url,
        access_key=access_key,
        secret_key=secret_key,
    )

    quarantine = UnifiedQuarantine(
        base_path=f"s3://{s3_config.bucket_silver}/common/quarantine",
        storage_options=storage_options,
    )

    lock = RedisDistributedLock(redis_client=redis_client)

    # Metrics - use PrometheusMetrics by default, NoOpMetrics only if explicitly disabled
    metrics: MetricsPort
    if getattr(settings, "metrics", None) and not settings.metrics.enabled:
        metrics = NoOpMetrics(warn_on_use=False)
    else:
        metrics = PrometheusMetrics()

    return ServiceContainer(
        checkpoint=checkpoint,
        quarantine=quarantine,
        lock=lock,
        metrics=metrics,
        redis_client=redis_client,
    )


class ChEMBLActivityPipelineFactory:
    """Factory for creating ChEMBL Activity pipelines.

    This factory lives in the composition root (bootstrap) because it needs
    to wire up infrastructure components to create a complete pipeline.

    Example (new API - recommended):
        >>> runtime = PipelineRuntimeConfig(run_type=RunType.INCREMENTAL)
        >>> pipeline = await ChEMBLActivityPipelineFactory.create_with_services(
        ...     runtime=runtime,
        ...     settings=get_settings(),
        ...     logger=logger,
        ... )
        >>> await pipeline.run()

    Example (legacy API - deprecated):
        >>> pipeline = await ChEMBLActivityPipelineFactory.create(
        ...     run_type=RunType.INCREMENTAL,
        ...     settings=get_settings(),
        ...     logger=logger,
        ... )
    """

    @staticmethod
    def build_services(
        settings: Settings,
        logger: "structlog.BoundLogger",
        metrics: MetricsPort | None = None,
        checkpoint: "CheckpointPort | None" = None,
        quarantine: "QuarantinePort | None" = None,
        lock: "LockPort | None" = None,
    ) -> PipelineServices:
        """Build PipelineServices from settings.

        Creates all necessary infrastructure adapters and returns them
        wrapped in a PipelineServices container.

        Args:
            settings: Application settings.
            logger: Structured logger.
            metrics: Optional metrics service (creates PrometheusMetrics if None).
            checkpoint: Optional checkpoint service.
            quarantine: Optional quarantine service.
            lock: Optional lock service.

        Returns:
            PipelineServices with all ports initialized.
        """
        aws_config = settings.aws
        s3_config = settings.s3
        storage_options = settings.storage_options
        access_key, secret_key = get_aws_credentials(settings)

        # Data source (ChEMBL)
        bucket = TokenBucket(rate=10.0, capacity=20)
        circuit_breaker = CircuitBreaker(provider="chembl")
        http_client = UnifiedHTTPClient(bucket, circuit_breaker)
        data_source = ChemblAdapter(http_client=http_client)

        # Storage
        bronze_writer = BronzeWriter(
            bucket=s3_config.bucket_bronze,
            endpoint_url=aws_config.endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
        )
        silver_writer = DeltaWriter(
            base_path=f"s3://{s3_config.bucket_silver}",
            storage_options=storage_options,
        )
        gold_writer = DeltaWriter(
            base_path=f"s3://{s3_config.bucket_silver}",
            storage_options=storage_options,
        )
        storage = StorageAdapter(bronze_writer, silver_writer, gold_writer)

        # Lock (Redis)
        if lock is None:
            redis_client = create_redis_client(settings)
            lock = RedisDistributedLock(redis_client=redis_client)

        # Checkpoint (S3)
        if checkpoint is None:
            checkpoint = S3Checkpoint(
                bucket=s3_config.bucket_checkpoints,
                endpoint_url=aws_config.endpoint_url,
                access_key=access_key,
                secret_key=secret_key,
            )

        # Quarantine
        if quarantine is None:
            quarantine = UnifiedQuarantine(
                base_path=f"s3://{s3_config.bucket_silver}/common/quarantine",
                storage_options=storage_options,
            )

        # Metrics
        if metrics is None:
            if getattr(settings, "metrics", None) and not settings.metrics.enabled:
                metrics = NoOpMetrics(warn_on_use=False)
            else:
                metrics = PrometheusMetrics()

        return PipelineServices(
            data_source=data_source,
            storage=storage,
            lock=lock,
            checkpoint=checkpoint,
            quarantine=quarantine,
            metrics=metrics,
            logger=logger,
        )

    @staticmethod
    async def create_with_services(
        runtime: PipelineRuntimeConfig,
        settings: Settings,
        logger: "structlog.BoundLogger",
        metrics: MetricsPort | None = None,
        checkpoint: "CheckpointPort | None" = None,
        quarantine: "QuarantinePort | None" = None,
        lock: "LockPort | None" = None,
    ) -> "ChEMBLActivityPipeline":
        """Create ChEMBL Activity pipeline with decomposed config (new API).

        This is the recommended way to create pipelines per ADR-0005.

        Args:
            runtime: Runtime execution parameters.
            settings: Application settings.
            logger: Structured logger.
            metrics: Optional metrics service.
            checkpoint: Optional checkpoint service.
            quarantine: Optional quarantine service.
            lock: Optional lock service.

        Returns:
            Configured pipeline instance.
        """
        from bioetl.application.pipelines.chembl_activity import ChEMBLActivityPipeline

        services = ChEMBLActivityPipelineFactory.build_services(
            settings=settings,
            logger=logger,
            metrics=metrics,
            checkpoint=checkpoint,
            quarantine=quarantine,
            lock=lock,
        )

        return ChEMBLActivityPipeline.create(
            runtime=runtime,
            services=services,
            config=CHEMBL_ACTIVITY_CONFIG,
        )

    @staticmethod
    async def create(
        run_type: "RunType",
        settings: Settings,
        logger: "structlog.BoundLogger",
        metrics: MetricsPort,
        resume: bool = False,
        limit: int | None = None,
        checkpoint: "CheckpointPort | None" = None,
        quarantine: "QuarantinePort | None" = None,
        lock: "LockPort | None" = None,
    ) -> "ChEMBLActivityPipeline":
        """Create configured ChEMBL Activity pipeline (legacy API).

        DEPRECATED: Use create_with_services() instead.
        Will be removed after 2025-01-15.

        Args:
            run_type: Type of run (incremental, backfill, rebuild)
            settings: Application settings object
            logger: Structured logger
            metrics: Injected metrics service
            resume: Resume from checkpoint if available
            limit: Maximum number of records to process
            checkpoint: Injected checkpoint service (optional)
            quarantine: Injected quarantine service (optional)
            lock: Injected lock service (optional)

        Returns:
            Configured pipeline instance
        """
        import warnings

        warnings.warn(
            "ChEMBLActivityPipelineFactory.create() is deprecated. "
            "Use create_with_services() instead. "
            "Will be removed after 2025-01-15.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Delegate to new API
        runtime = PipelineRuntimeConfig(
            run_type=run_type,
            resume=resume,
            limit=limit,
        )

        return await ChEMBLActivityPipelineFactory.create_with_services(
            runtime=runtime,
            settings=settings,
            logger=logger,
            metrics=metrics,
            checkpoint=checkpoint,
            quarantine=quarantine,
            lock=lock,
        )
