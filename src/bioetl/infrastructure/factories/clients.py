"""Factories for creating infrastructure clients (e.g., Redis, S3).

This centralizes client initialization logic, making it reusable and consistent
across the application, especially in the composition root (bootstrap).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import redis.asyncio as aioredis

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings


def create_redis_client(settings: Settings) -> aioredis.Redis:
    """Create and configure a Redis client from application settings.

    Args:
        settings: The application settings object.

    Returns:
        An initialized aioredis.Redis client instance.
    """
    redis_config = settings.redis
    password = (
        redis_config.password.get_secret_value() if redis_config.password else None
    )
    return aioredis.Redis(
        host=redis_config.host,
        port=redis_config.port,
        password=password,
        db=redis_config.db,
        decode_responses=True,  # Ensure we get strings, not bytes
    )


def get_aws_credentials(settings: Settings) -> tuple[str | None, str | None]:
    """Extract AWS credentials (access key, secret key) from settings.

    Handles the secure extraction of the secret key from the SecretStr.

    Args:
        settings: The application settings object.

    Returns:
        A tuple containing the access key ID and the secret access key.
    """
    aws_config = settings.aws
    secret_key = (
        aws_config.secret_access_key.get_secret_value()
        if aws_config.secret_access_key
        else None
    )
    return aws_config.access_key_id, secret_key
