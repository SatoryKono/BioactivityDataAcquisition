"""Composition Root for BioETL.

Handles the initialization and wiring of infrastructure components (adapters)
to provide a ready-to-use dependency container for the application layer.

This is the only place where infrastructure imports are allowed to create
concrete implementations of domain ports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.config import Settings, get_settings
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
    """Container for initialized infrastructure services."""

    checkpoint: CheckpointPort
    quarantine: QuarantinePort
    lock: LockPort
    # We expose raw configs/clients if needed by factories, though ideally
    # everything should be behind a Port.
    redis_client: aioredis.Redis


def bootstrap() -> ServiceContainer:
    """Initialize all infrastructure services.

    Returns:
        ServiceContainer with ready-to-use adapters.
    """
    # Load configuration
    settings = get_settings()
    aws_config = settings.aws
    s3_config = settings.s3
    storage_options = settings.get_storage_options()

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

    return ServiceContainer(
        checkpoint=checkpoint,
        quarantine=quarantine,
        lock=lock,
        redis_client=redis_client,
    )


class ChEMBLActivityPipelineFactory:
    """Factory for creating ChEMBL Activity pipelines.

    This factory lives in the composition root (bootstrap) because it needs
    to wire up infrastructure components to create a complete pipeline.

    Example:
        >>> pipeline = await ChEMBLActivityPipelineFactory.create(
        ...     run_type=RunType.INCREMENTAL,
        ...     settings=get_settings(),
        ... )
        >>> await pipeline.run()
    """

    @staticmethod
    async def create(
        run_type: RunType,
        settings: Settings,
        logger: structlog.BoundLogger,
        resume: bool = False,
        checkpoint: CheckpointPort | None = None,
        quarantine: QuarantinePort | None = None,
        lock: LockPort | None = None,
    ) -> ChEMBLActivityPipeline:
        """Create configured ChEMBL Activity pipeline.

        Args:
            run_type: Type of run (incremental, backfill, rebuild)
            settings: Application settings object
            logger: Structured logger
            resume: Resume from checkpoint if available
            checkpoint: Injected checkpoint service (optional)
            quarantine: Injected quarantine service (optional)
            lock: Injected lock service (optional)

        Returns:
            Configured pipeline instance
        """
        # Import here to avoid circular imports
        from bioetl.application.pipelines.chembl_activity import ChEMBLActivityPipeline

        # Config shortcuts
        aws_config = settings.aws
        s3_config = settings.s3
        storage_options = settings.get_storage_options()

        # Data source (ChEMBL)
        bucket = TokenBucket(rate=10.0, capacity=20)
        circuit_breaker = CircuitBreaker(provider="chembl")
        http_client = UnifiedHTTPClient(bucket, circuit_breaker)
        data_source = ChemblAdapter(http_client=http_client)

        # Storage
        access_key, secret_key = get_aws_credentials(settings)
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
            # Use the factory to create the client
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

        return ChEMBLActivityPipeline(
            run_type=run_type,
            data_source=data_source,
            storage=storage,
            lock=lock,
            checkpoint=checkpoint,
            quarantine=quarantine,
            logger=logger,
            resume=resume,
        )
