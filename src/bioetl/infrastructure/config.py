"""Infrastructure configuration adapters.

Provides backward-compatible functions for accessing configuration.
All configuration is loaded from the centralized bioetl.config module.

Usage:
    from bioetl.infrastructure.config import get_aws_config, get_storage_options

    # Get AWS config
    config = get_aws_config()

    # Get storage options for Delta Lake
    storage_opts = get_storage_options()
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.config import get_settings


@dataclass(frozen=True)
class AWSConfig:
    """AWS configuration.

    Attributes:
        endpoint_url: Custom endpoint URL (for LocalStack/MinIO)
        access_key_id: AWS access key ID
        secret_access_key: AWS secret access key
        region: AWS region (default: us-east-1)
    """

    endpoint_url: str | None
    access_key_id: str | None
    secret_access_key: str | None
    region: str

    @property
    def is_configured(self) -> bool:
        """Check if AWS credentials are configured."""
        return bool(self.access_key_id and self.secret_access_key)


@dataclass(frozen=True)
class S3Config:
    """S3 bucket configuration.

    Attributes:
        bucket_bronze: Bronze layer bucket name
        bucket_silver: Silver layer bucket name
        bucket_gold: Gold layer bucket name
        bucket_checkpoints: Checkpoints bucket name
    """

    bucket_bronze: str
    bucket_silver: str
    bucket_gold: str
    bucket_checkpoints: str


@dataclass(frozen=True)
class RedisConfig:
    """Redis configuration.

    Attributes:
        host: Redis host
        port: Redis port
    """

    host: str
    port: int


def get_aws_config() -> AWSConfig:
    """Load AWS configuration from centralized settings.

    Returns:
        AWSConfig instance
    """
    aws = get_settings().aws
    secret = aws.secret_access_key
    return AWSConfig(
        endpoint_url=aws.endpoint_url,
        access_key_id=aws.access_key_id,
        secret_access_key=secret.get_secret_value() if secret else None,
        region=aws.region,
    )


def get_s3_config() -> S3Config:
    """Load S3 bucket configuration from centralized settings.

    Returns:
        S3Config instance
    """
    s3 = get_settings().s3
    return S3Config(
        bucket_bronze=s3.bucket_bronze,
        bucket_silver=s3.bucket_silver,
        bucket_gold=s3.bucket_gold,
        bucket_checkpoints=s3.bucket_checkpoints,
    )


def get_redis_config() -> RedisConfig:
    """Load Redis configuration from centralized settings.

    Returns:
        RedisConfig instance
    """
    redis = get_settings().redis
    return RedisConfig(
        host=redis.host,
        port=redis.port,
    )


def get_storage_options() -> dict[str, str] | None:
    """Get storage options for Delta Lake/Polars.

    Returns dictionary suitable for Delta Lake and Polars storage_options
    parameter. Returns None if custom endpoint is not configured.

    Returns:
        Storage options dict or None
    """
    return get_settings().get_storage_options()
