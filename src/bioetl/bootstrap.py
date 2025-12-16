"""Composition Root for BioETL.

Handles the initialization and wiring of infrastructure components (adapters)
to provide a ready-to-use dependency container for the application layer.

This is the only place where infrastructure imports are allowed to create
concrete implementations of domain ports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import redis.asyncio as aioredis

from bioetl.config import Settings, get_settings
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.factories.storage import StorageAdapter
from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter

if TYPE_CHECKING:
    from bioetl.application.pipelines.chembl_activity import ChEMBLActivityPipeline
    from bioetl.domain.ports import CheckpointPort, LockPort, QuarantinePort
    from bioetl.domain.types import RunType


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
    redis_config = settings.redis
    storage_options = settings.get_storage_options()

    # Initialize Redis Client (Infrastructure)
    redis_client = aioredis.Redis(
        host=redis_config.host,
        port=redis_config.port,
        password=(
            redis_config.password.get_secret_value() if redis_config.password else None
        ),
        db=redis_config.db,
        decode_responses=True,  # Ensure we get strings
    )

    # Initialize Adapters
    secret_key = (
        aws_config.secret_access_key.get_secret_value()
        if aws_config.secret_access_key
        else None
    )
    checkpoint = S3Checkpoint(
        bucket=s3_config.bucket_checkpoints,
        endpoint_url=aws_config.endpoint_url,
        access_key=aws_config.access_key_id,
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
        resume: bool = False,
        checkpoint: CheckpointPort | None = None,
        quarantine: QuarantinePort | None = None,
        lock: LockPort | None = None,
    ) -> ChEMBLActivityPipeline:
        """Create configured ChEMBL Activity pipeline.

        Args:
            run_type: Type of run (incremental, backfill, rebuild)
            settings: Application settings object
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
        redis_config = settings.redis
        storage_options = settings.get_storage_options()

        # Data source (ChEMBL)
        bucket = TokenBucket(rate=10.0, capacity=20)
        circuit_breaker = CircuitBreaker(provider="chembl")
        http_client = UnifiedHTTPClient(bucket, circuit_breaker)
        data_source = ChemblAdapter(http_client=http_client)

        # Storage
        secret_key = (
            aws_config.secret_access_key.get_secret_value()
            if aws_config.secret_access_key
            else None
        )
        bronze_writer = BronzeWriter(
            bucket=s3_config.bucket_bronze,
            endpoint_url=aws_config.endpoint_url,
            access_key=aws_config.access_key_id,
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
            redis_client = aioredis.Redis(
                host=redis_config.host,
                port=redis_config.port,
                password=(
                    redis_config.password.get_secret_value()
                    if redis_config.password
                    else None
                ),
                db=redis_config.db,
            )
            lock = RedisDistributedLock(redis_client=redis_client)

        # Checkpoint (S3)
        if checkpoint is None:
            checkpoint = S3Checkpoint(
                bucket=s3_config.bucket_checkpoints,
                endpoint_url=aws_config.endpoint_url,
                access_key=aws_config.access_key_id,
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
            resume=resume,
        )
