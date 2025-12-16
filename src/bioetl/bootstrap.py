"""Composition Root for BioETL.

Handles the initialization and wiring of infrastructure components (adapters)
to provide a ready-to-use dependency container for the application layer.

This is the only place where infrastructure imports are allowed to create
concrete implementations of domain ports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.config import get_settings
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint

# Re-export factories for convenience and backward compatibility if needed,
# though direct import is preferred.
from bioetl.infrastructure.factories.clients import (
    create_redis_client,
    get_aws_credentials,
)
from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock
from bioetl.infrastructure.observability.logging import (
    create_logger as create_infra_logger,
)
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine

if TYPE_CHECKING:
    from uuid import UUID

    import redis.asyncio as aioredis
    import structlog

    from bioetl.domain.ports import CheckpointPort, LockPort, QuarantinePort


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
