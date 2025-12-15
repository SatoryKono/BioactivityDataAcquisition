"""Centralized configuration for BioETL infrastructure.

Provides single source of truth for:
- AWS configuration (credentials, endpoints)
- S3 bucket configuration
- Redis configuration
- Storage options for Delta Lake

Usage:
    from bioetl.infrastructure.config import get_aws_config, get_storage_options

    # Get AWS config
    config = get_aws_config()

    # Get storage options for Delta Lake
    storage_opts = get_storage_options()
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AWSConfig:
    """AWS configuration loaded from environment variables.

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
    """Load AWS configuration from environment variables.

    Environment variables:
        AWS_ENDPOINT_URL: Custom endpoint (optional)
        AWS_ACCESS_KEY_ID: Access key ID
        AWS_SECRET_ACCESS_KEY: Secret access key
        AWS_DEFAULT_REGION: Region (default: us-east-1)

    Returns:
        AWSConfig instance
    """
    return AWSConfig(
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )


def get_s3_config() -> S3Config:
    """Load S3 bucket configuration from environment variables.

    Environment variables:
        BIOETL_S3_BUCKET_BRONZE: Bronze bucket (default: bioetl-bronze)
        BIOETL_S3_BUCKET_SILVER: Silver bucket (default: bioetl-silver)
        BIOETL_S3_BUCKET_GOLD: Gold bucket (default: bioetl-gold)
        BIOETL_S3_BUCKET_CHECKPOINTS: Checkpoints bucket (default: bioetl-checkpoints)

    Returns:
        S3Config instance
    """
    return S3Config(
        bucket_bronze=os.getenv("BIOETL_S3_BUCKET_BRONZE", "bioetl-bronze"),
        bucket_silver=os.getenv("BIOETL_S3_BUCKET_SILVER", "bioetl-silver"),
        bucket_gold=os.getenv("BIOETL_S3_BUCKET_GOLD", "bioetl-gold"),
        bucket_checkpoints=os.getenv("BIOETL_S3_BUCKET_CHECKPOINTS", "bioetl-checkpoints"),
    )


def get_redis_config() -> RedisConfig:
    """Load Redis configuration from environment variables.

    Environment variables:
        BIOETL_REDIS_HOST: Redis host (default: localhost)
        BIOETL_REDIS_PORT: Redis port (default: 6379)

    Returns:
        RedisConfig instance
    """
    return RedisConfig(
        host=os.getenv("BIOETL_REDIS_HOST", "localhost"),
        port=int(os.getenv("BIOETL_REDIS_PORT", "6379")),
    )


def get_storage_options() -> dict[str, str] | None:
    """Get storage options for Delta Lake/Polars.

    Returns dictionary suitable for Delta Lake and Polars storage_options
    parameter. Returns None if custom endpoint is not configured.

    Returns:
        Storage options dict or None
    """
    aws_config = get_aws_config()

    if not aws_config.endpoint_url:
        return None

    return {
        "AWS_ENDPOINT_URL": aws_config.endpoint_url,
        "AWS_ACCESS_KEY_ID": aws_config.access_key_id or "",
        "AWS_SECRET_ACCESS_KEY": aws_config.secret_access_key or "",
    }
