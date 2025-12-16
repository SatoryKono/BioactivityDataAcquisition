"""Composition Root for BioETL.

Handles the initialization and wiring of infrastructure components (adapters)
to provide a ready-to-use dependency container for the application layer.
"""

from dataclasses import dataclass
from typing import Optional

import redis.asyncio as aioredis

from bioetl.domain.ports import CheckpointPort, LockPort, QuarantinePort
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.config import (
    get_aws_config,
    get_redis_config,
    get_s3_config,
    get_storage_options,
)
from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine


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
    aws_config = get_aws_config()
    s3_config = get_s3_config()
    redis_config = get_redis_config()
    storage_options = get_storage_options()

    # Initialize Redis Client (Infrastructure)
    redis_client = aioredis.Redis(
        host=redis_config.host,
        port=redis_config.port,
        decode_responses=True,  # Ensure we get strings
    )

    # Initialize Adapters
    checkpoint = S3Checkpoint(
        bucket=s3_config.bucket_checkpoints,
        endpoint_url=aws_config.endpoint_url,
        access_key=aws_config.access_key_id,
        secret_key=aws_config.secret_access_key,
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
