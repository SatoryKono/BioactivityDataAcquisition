"""Centralized configuration for BioETL.

Uses pydantic-settings for type-safe, validated configuration from environment
variables and YAML files. All settings are loaded once at startup and validated.

Usage:
    from bioetl.config import get_settings

    settings = get_settings()
    print(settings.s3.bucket_bronze)
    print(settings.redis.host)
"""

from __future__ import annotations

import warnings
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


def yaml_config_settings_source() -> dict[str, Any]:
    """
    A simple settings source that loads variables from a YAML file
    at the project's root.
    """
    try:
        with Path("config.yaml").open() as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}


class AWSSettings(BaseSettings):
    """AWS credentials and endpoint configuration."""

    model_config = SettingsConfigDict(frozen=True)

    access_key_id: str | None = Field(default=None)
    secret_access_key: SecretStr | None = Field(default=None)
    endpoint_url: str | None = Field(default=None)
    default_region: str = Field(default="us-east-1")

    @property
    def region(self) -> str:
        """Alias for default_region for backward compatibility."""
        return self.default_region

    @property
    def is_configured(self) -> bool:
        """Check if AWS credentials are configured."""
        return bool(self.access_key_id and self.secret_access_key)


class S3Settings(BaseSettings):
    """S3 bucket configuration."""

    model_config = SettingsConfigDict(frozen=True)

    bucket_bronze: str = Field(default="bioetl-bronze")
    bucket_silver: str = Field(default="bioetl-silver")
    bucket_gold: str = Field(default="bioetl-gold")
    bucket_checkpoints: str = Field(default="bioetl-checkpoints")


class RedisSettings(BaseSettings):
    """Redis connection configuration."""

    model_config = SettingsConfigDict(frozen=True)

    host: str = Field(default="localhost")
    port: int = Field(default=6379, ge=1, le=65535)
    password: SecretStr | None = Field(default=None)
    db: int = Field(default=0, ge=0)


class PipelineSettings(BaseSettings):
    """Pipeline execution configuration."""

    model_config = SettingsConfigDict(frozen=True)

    batch_size: int = Field(default=100, ge=1, le=10000)
    """Number of records per batch write."""

    checkpoint_interval: int = Field(default=1000, ge=100)
    """Save checkpoint every N records."""

    max_concurrent_batches: int = Field(default=4, ge=1, le=16)
    """Maximum concurrent batch writes."""

    heartbeat_interval: int = Field(default=20, ge=5, le=60)
    """Lock heartbeat interval in seconds (default: 20s, range: 5-60s)."""


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_prefix="BIOETL_",
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    env: Literal["dev", "staging", "prod"] = Field(default="dev")
    debug: bool = Field(default=False)
    test_mode: bool = Field(default=False)
    strict_error_handling: bool = Field(
        default=False,
        description="When True, API client errors raise exceptions instead of being silently ignored. "
                    "Recommended for dev/staging environments.",
    )

    aws: AWSSettings = Field(default_factory=AWSSettings)
    s3: S3Settings = Field(default_factory=S3Settings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)

    @model_validator(mode="after")
    def check_s3_endpoint_for_dev(self) -> Settings:
        if self.test_mode:
            return self
        if self.env == "dev" and self.aws.endpoint_url is None:
            raise ValueError("aws.endpoint_url must be set in dev environment")
        return self

    def get_storage_options(self) -> dict[str, str] | None:
        """Get storage options for Delta Lake/Polars."""
        if not self.aws.endpoint_url:
            return None

        secret = self.aws.secret_access_key
        return {
            "AWS_ENDPOINT_URL": self.aws.endpoint_url,
            "AWS_ACCESS_KEY_ID": self.aws.access_key_id or "",
            "AWS_SECRET_ACCESS_KEY": secret.get_secret_value() if secret else "",
        }

    @classmethod
    def settings_customise_sources(
        cls,
        _settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            dotenv_settings,
            yaml_config_settings_source,
            init_settings,
            file_secret_settings,
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Deprecated aliases - use *Settings classes instead
_DEPRECATED_ALIASES: dict[str, type] = {
    "AWSConfig": AWSSettings,
    "S3Config": S3Settings,
    "RedisConfig": RedisSettings,
    "PipelineConfig": PipelineSettings,
}


def __getattr__(name: str) -> Any:
    """Provide deprecation warnings for old config class names."""
    if name in _DEPRECATED_ALIASES:
        warnings.warn(
            f"{name} is deprecated, use {_DEPRECATED_ALIENCES[name].__name__} instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return _DEPRECATED_ALIASES[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_aws_config() -> AWSSettings:
    return get_settings().aws


def get_s3_config() -> S3Settings:
    return get_settings().s3


def get_redis_config() -> RedisSettings:
    return get_settings().redis


def get_pipeline_config() -> PipelineSettings:
    return get_settings().pipeline


def get_storage_options() -> dict[str, str] | None:
    return get_settings().get_storage_options()
