"""Centralized configuration for BioETL.

Uses pydantic-settings for type-safe, validated configuration from environment
variables and YAML files. All settings are loaded once at startup and validated.

Usage:
    from bioetl.infrastructure.config import get_settings

    settings = get_settings()
    print(settings.s3.bucket_bronze)
    print(settings.redis.host)
"""

from __future__ import annotations

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

from bioetl.domain.pipeline_config import PipelineConfig
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class YamlSettingsSource(PydanticBaseSettingsSource):
    """
    A settings source that loads variables from a YAML file.
    """

    def get_field_value(
        self, field: Field, field_name: str
    ) -> tuple[Any, str] | None:
        """
        Get value of a field from YAML file.
        """
        encoding = self.config.get("env_file_encoding")
        try:
            with Path("config.yaml").open(encoding=encoding) as f:
                file_content = yaml.safe_load(f)
        except FileNotFoundError:
            return None

        if not isinstance(file_content, dict):
            return None

        field_value = file_content.get(field_name)
        return field_value, field_name

    def prepare_field_value(
        self, field_name: str, field: Field, value: Any
    ) -> Any:
        """
        Prepare value of a field.
        """
        return value

    def __call__(self) -> dict[str, Any]:
        d: dict[str, Any] = {}

        for field_name, field in self.settings_cls.model_fields.items():
            field_value_and_key = self.get_field_value(field, field_name)
            if field_value_and_key is None:
                continue

            field_value, field_key = field_value_and_key
            if field_value is not None:
                field_value = self.prepare_field_value(
                    field_name, field, field_value
                )
                d[field_key] = field_value

        return d


def load_pipeline_config(pipeline_name: str) -> dict[str, Any]:
    """Load pipeline configuration from YAML file.

    Args:
        pipeline_name: Name of the pipeline (e.g., 'chembl_activity')

    Returns:
        Dictionary with pipeline configuration (including merged source config)
    """
    # Map pipeline name to config path
    config_paths = {
        "chembl_activity": Path("configs/pipelines/chembl/activity.yaml"),
    }

    config_path = config_paths.get(pipeline_name)
    if not config_path or not config_path.exists():
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    # Load source config from separate file if specified
    if source_file := config.get("source_file"):
        source_path = config_path.parent / source_file
        if source_path.exists():
            with open(source_path, "r", encoding="utf-8") as f:
                source_config = yaml.safe_load(f) or {}
            # Merge source config into main config
            config["source"] = source_config.get("source", source_config)

    return config


@lru_cache(maxsize=10)
def get_pipeline_config(pipeline_name: str) -> PipelineConfig:
    """Get PipelineConfig object from YAML configuration.

    Args:
        pipeline_name: Name of the pipeline (e.g., 'chembl_activity')

    Returns:
        PipelineConfig instance

    Raises:
        ValueError: If pipeline configuration not found
    """
    config_data = load_pipeline_config(pipeline_name)
    if not config_data:
        raise ValueError(f"Pipeline configuration not found: {pipeline_name}")

    # Extract field names from source config
    source_fields = [
        field["name"] for field in config_data.get("source", {}).get("fields", [])
    ]

    # Validate against strict schema
    # Use default values if keys are missing to allow partial configs during migration
    validated_config = PipelineYamlConfig(
        pipeline_name=pipeline_name,
        provider=config_data.get("provider", pipeline_name.split("_")[0]),
        entity_type=config_data.get("entity_type", pipeline_name.split("_")[-1]),
        primary_keys=config_data.get("primary_keys", ["id"]),
        silver_table=config_data.get("silver_table", f"{pipeline_name}.data"),
        gold_table=config_data.get("gold_table", f"{pipeline_name}.data_gold"),
        batch_size=config_data.get("batch_size", 100),
        checkpoint_interval=config_data.get("checkpoint_interval", 1000),
        # Pass other fields if needed or allow default
    )

    # Map validated config to Domain PipelineConfig
    return PipelineConfig(
        pipeline_name=validated_config.pipeline_name,
        provider=validated_config.provider,
        entity_type=validated_config.entity_type,
        primary_keys=validated_config.primary_keys,
        silver_table=validated_config.silver_table,
        gold_table=validated_config.gold_table,
        batch_size=validated_config.batch_size,
        checkpoint_interval=validated_config.checkpoint_interval,
        fields=source_fields,
    )


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

    @property
    def storage_options(self) -> dict[str, str] | None:
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
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            dotenv_settings,
            YamlSettingsSource(settings_cls),
            init_settings,
            file_secret_settings,
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
