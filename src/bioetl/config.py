"""Centralized configuration for BioETL.

Uses pydantic-settings for type-safe, validated configuration from environment
variables. All settings are loaded once at startup and validated.

Usage:
    from bioetl.config import get_settings

    settings = get_settings()
    print(settings.s3.bucket_bronze)
    print(settings.redis.host)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AWSSettings(BaseSettings):
    """AWS credentials and endpoint configuration."""

    model_config = SettingsConfigDict(env_prefix="AWS_", extra="ignore")

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

    model_config = SettingsConfigDict(env_prefix="BIOETL_S3_", extra="ignore")

    bucket_bronze: str = Field(default="bioetl-bronze")
    bucket_silver: str = Field(default="bioetl-silver")
    bucket_gold: str = Field(default="bioetl-gold")
    bucket_checkpoints: str = Field(default="bioetl-checkpoints")


class RedisSettings(BaseSettings):
    """Redis connection configuration."""

    model_config = SettingsConfigDict(env_prefix="BIOETL_REDIS_", extra="ignore")

    host: str = Field(default="localhost")
    port: int = Field(default=6379, ge=1, le=65535)
    password: SecretStr | None = Field(default=None)
    db: int = Field(default=0, ge=0)


class LockSettings(BaseSettings):
    """Distributed lock configuration."""

    model_config = SettingsConfigDict(env_prefix="BIOETL_LOCK_", extra="ignore")

    ttl: int = Field(default=60, ge=1, description="Lock TTL in seconds")
    heartbeat_interval: int = Field(default=20, ge=1)
    max_duration: int = Field(default=14400, ge=60, description="4 hours max")


class ObservabilitySettings(BaseSettings):
    """Logging and metrics configuration."""

    model_config = SettingsConfigDict(env_prefix="BIOETL_", extra="ignore")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )
    log_format: Literal["json", "text"] = Field(default="json")
    log_file: str | None = Field(default="logs/bioetl.log")
    metrics_port: int = Field(default=9090, ge=1, le=65535)
    metrics_enabled: bool = Field(default=True)


class DataQualitySettings(BaseSettings):
    """Data quality thresholds configuration."""

    model_config = SettingsConfigDict(env_prefix="BIOETL_DQ_", extra="ignore")

    soft_threshold: float = Field(default=0.05, ge=0, le=1)
    hard_threshold: float = Field(default=0.20, ge=0, le=1)
    baseline_days: int = Field(default=30, ge=1)
    anomaly_warning_multiplier: float = Field(default=2.0, ge=1)
    anomaly_critical_multiplier: float = Field(default=5.0, ge=1)

    @field_validator("hard_threshold")
    @classmethod
    def hard_must_be_gte_soft(cls, v: float, info) -> float:
        """Ensure hard threshold >= soft threshold."""
        soft = info.data.get("soft_threshold", 0.05)
        if v < soft:
            msg = f"hard_threshold ({v}) must be >= soft_threshold ({soft})"
            raise ValueError(msg)
        return v


class CircuitBreakerSettings(BaseSettings):
    """Circuit breaker configuration."""

    model_config = SettingsConfigDict(env_prefix="BIOETL_CB_", extra="ignore")

    failure_threshold: int = Field(default=5, ge=1)
    recovery_timeout: int = Field(default=300, ge=1, description="5 minutes")
    open_alert_threshold: int = Field(default=600, ge=1, description="10 minutes")


class RetrySettings(BaseSettings):
    """Retry policy configuration."""

    model_config = SettingsConfigDict(env_prefix="BIOETL_RETRY_", extra="ignore")

    max_attempts: int = Field(default=3, ge=1, le=10)
    multiplier: float = Field(default=2.0, ge=1)
    jitter_min: float = Field(default=0.1, ge=0, le=1)
    jitter_max: float = Field(default=0.5, ge=0, le=1)


class DeltaLakeSettings(BaseSettings):
    """Delta Lake configuration."""

    model_config = SettingsConfigDict(env_prefix="BIOETL_DELTA_", extra="ignore")

    vacuum_retention: int = Field(default=7, ge=1, description="Days")
    forensic_retention: int = Field(default=7, ge=1, description="Days")


class PartitionSettings(BaseSettings):
    """Partitioning thresholds configuration."""

    model_config = SettingsConfigDict(env_prefix="BIOETL_PARTITION_", extra="ignore")

    warning_threshold: int = Field(default=10000, ge=100)
    hard_limit: int = Field(default=50000, ge=1000)
    files_per_partition_warning: int = Field(default=100, ge=10)


class QuarantineSettings(BaseSettings):
    """Quarantine configuration."""

    model_config = SettingsConfigDict(env_prefix="BIOETL_QUARANTINE_", extra="ignore")

    retention_days: int = Field(default=30, ge=1)
    payload_max_size: int = Field(default=65536, ge=1024, description="64KB")


class DisasterRecoverySettings(BaseSettings):
    """Disaster recovery configuration."""

    model_config = SettingsConfigDict(env_prefix="BIOETL_DR_", extra="ignore")

    rpo_hours: int = Field(default=24, ge=1)
    rto_hours: int = Field(default=4, ge=1)
    backup_enabled: bool = Field(default=True)


class Settings(BaseSettings):
    """Main application settings.

    Aggregates all setting groups and provides a single entry point
    for configuration access. Settings are loaded from environment
    variables and validated at startup.

    Raises:
        ValidationError: If required settings are missing or invalid.
    """

    model_config = SettingsConfigDict(
        env_prefix="BIOETL_",
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Environment
    env: Literal["dev", "staging", "prod"] = Field(default="dev")
    debug: bool = Field(default=False)
    test_mode: bool = Field(default=False)

    # Nested settings (loaded separately to handle different prefixes)
    @property
    def aws(self) -> AWSSettings:
        """AWS configuration."""
        return AWSSettings()

    @property
    def s3(self) -> S3Settings:
        """S3 bucket configuration."""
        return S3Settings()

    @property
    def redis(self) -> RedisSettings:
        """Redis configuration."""
        return RedisSettings()

    @property
    def lock(self) -> LockSettings:
        """Lock configuration."""
        return LockSettings()

    @property
    def observability(self) -> ObservabilitySettings:
        """Observability configuration."""
        return ObservabilitySettings()

    @property
    def data_quality(self) -> DataQualitySettings:
        """Data quality configuration."""
        return DataQualitySettings()

    @property
    def circuit_breaker(self) -> CircuitBreakerSettings:
        """Circuit breaker configuration."""
        return CircuitBreakerSettings()

    @property
    def retry(self) -> RetrySettings:
        """Retry policy configuration."""
        return RetrySettings()

    @property
    def delta_lake(self) -> DeltaLakeSettings:
        """Delta Lake configuration."""
        return DeltaLakeSettings()

    @property
    def partition(self) -> PartitionSettings:
        """Partition configuration."""
        return PartitionSettings()

    @property
    def quarantine(self) -> QuarantineSettings:
        """Quarantine configuration."""
        return QuarantineSettings()

    @property
    def disaster_recovery(self) -> DisasterRecoverySettings:
        """Disaster recovery configuration."""
        return DisasterRecoverySettings()

    def get_storage_options(self) -> dict[str, str] | None:
        """Get storage options for Delta Lake/Polars.

        Returns dictionary suitable for Delta Lake and Polars storage_options
        parameter. Returns None if custom endpoint is not configured.
        """
        aws = self.aws
        if not aws.endpoint_url:
            return None

        secret = aws.secret_access_key
        return {
            "AWS_ENDPOINT_URL": aws.endpoint_url,
            "AWS_ACCESS_KEY_ID": aws.access_key_id or "",
            "AWS_SECRET_ACCESS_KEY": secret.get_secret_value() if secret else "",
        }


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Settings are loaded once and cached for the lifetime of the application.
    This ensures consistent configuration across all modules.

    Returns:
        Settings: Validated application settings.

    Raises:
        ValidationError: If required settings are missing or invalid.
    """
    return Settings()
