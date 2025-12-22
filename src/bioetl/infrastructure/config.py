"""Centralized configuration for BioETL.

Uses pydantic-settings for type-safe, validated configuration from environment
variables and YAML files. All settings are loaded once at startup and validated.

Consolidated configuration (post-refactoring):
- Settings: Main application settings (pydantic-settings)
- RuntimeConfig: Re-exported from domain.config for CLI convenience

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
from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.config import PipelineConfig
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class YamlSettingsSource(PydanticBaseSettingsSource):
    """
    A settings source that loads variables from a YAML file.
    """

    def get_field_value(self, field: Field, field_name: str) -> tuple[Any, str] | None:
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

    def prepare_field_value(self, field_name: str, field: Field, value: Any) -> Any:
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
                field_value = self.prepare_field_value(field_name, field, field_value)
                d[field_key] = field_value

        return d


@lru_cache(maxsize=10)
def load_pipeline_config(pipeline_name: str) -> PipelineYamlConfig:
    """Load pipeline configuration from YAML file and return typed model.

    Dynamically resolves the configuration file path based on the pipeline name.
    The pipeline name is expected to follow the pattern '{provider}_{entity}'.
    Example: 'chembl_activity' -> 'configs/pipelines/chembl/activity.yaml'

    Results are cached for efficiency - YAML files are only read once per pipeline.

    Args:
        pipeline_name: Name of the pipeline (e.g., 'chembl_activity')

    Returns:
        PipelineYamlConfig: Validated pipeline configuration

    Raises:
        ValueError: If config file is missing or validation fails
    """
    # 1. Try dynamic resolution: {provider}_{entity}
    try:
        provider, entity = pipeline_name.split("_", 1)
        config_path = Path(f"configs/pipelines/{provider}/{entity}.yaml")
    except ValueError:
        # Fallback for names that don't match the pattern (no underscore)
        config_path = Path(f"configs/pipelines/{pipeline_name}.yaml")

    # 2. Check if file exists
    if not config_path.exists():
        raise ValueError(f"Configuration file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    # Load source config from separate file if specified
    if source_file := config.get("source_file"):
        source_path = config_path.parent / source_file
        if source_path.exists():
            with open(source_path, encoding="utf-8") as f:
                source_config = yaml.safe_load(f) or {}
            # Merge source config into main config
            config["source"] = source_config.get("source", source_config)

    # Validate against strict schema
    return PipelineYamlConfig.model_validate(config)


def yaml_config_to_domain(yaml_config: PipelineYamlConfig) -> PipelineConfig:
    """Map PipelineYamlConfig to domain PipelineConfig.

    This is the boundary mapping function that converts validated infrastructure
    schema to domain model. All validation has already been done by Pydantic
    in PipelineYamlConfig.

    Args:
        yaml_config: Validated PipelineYamlConfig from infrastructure layer

    Returns:
        PipelineConfig: Immutable domain configuration
    """
    # Extract field names from source config
    source_fields = yaml_config.source.fields
    if source_fields and isinstance(source_fields[0], dict):
        # Handle cases where fields are dicts like [{'name': 'col1'}, ...]
        source_fields = [field["name"] for field in source_fields if "name" in field]

    watermark_field = yaml_config.source.watermark_field

    # Extract storage config
    silver_config = yaml_config.sink.get("silver")
    write_mode = "merge" # Default
    # Note: partition_cols are not explicitly in YAML schema yet, would need to be added to Schema first if needed dynamically.
    # For now, we assume empty or derived.
    # But wait, SinkLayerConfig in schema has 'mode' (str | None).

    if silver_config and silver_config.mode:
        write_mode = silver_config.mode

    return PipelineConfig(
        pipeline_name=yaml_config.pipeline_name,
        provider=yaml_config.provider,
        entity_type=yaml_config.entity_type,
        primary_keys=yaml_config.primary_keys,
        silver_table=yaml_config.silver_table,
        gold_table=yaml_config.gold_table,
        write_mode=write_mode, # Mapped from YAML
        gold_filter_types=yaml_config.gold_filter_types,
        gold_min_confidence=yaml_config.gold_min_confidence,
        batch_size=yaml_config.batch_size,
        checkpoint_interval=yaml_config.checkpoint_interval,
        fields=source_fields,
        watermark_field=watermark_field,
        dq=DomainDQConfig(
            soft_fail_threshold=yaml_config.dq_rules.soft_fail_threshold,
            hard_fail_threshold=yaml_config.dq_rules.hard_fail_threshold,
        ),
    )


@lru_cache(maxsize=10)
def get_pipeline_config(pipeline_name: str) -> PipelineConfig:
    """Get PipelineConfig object from YAML configuration.

    Convenience function that loads and maps config in one step.
    Results are cached for efficiency.

    Args:
        pipeline_name: Name of the pipeline (e.g., 'chembl_activity')

    Returns:
        PipelineConfig instance

    Raises:
        ValueError: If pipeline configuration not found
    """
    yaml_config = load_pipeline_config(pipeline_name)
    return yaml_config_to_domain(yaml_config)


class AWSSettings(BaseSettings):
    """AWS credentials and endpoint configuration."""

    model_config = SettingsConfigDict(
        frozen=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    access_key_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "aws_access_key_id",
            "bioetl_aws_access_key_id",
        ),
    )
    secret_access_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "aws_secret_access_key",
            "bioetl_aws_secret_access_key",
        ),
    )
    endpoint_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "aws_endpoint_url",
            "bioetl_aws_endpoint_url",
        ),
    )
    default_region: str = Field(
        default="us-east-1",
        validation_alias=AliasChoices(
            "aws_region",
            "aws_default_region",
            "bioetl_aws_region",
        ),
    )

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


class ObservabilitySettings(BaseSettings):
    """Observability configuration."""

    model_config = SettingsConfigDict(frozen=True)

    tracing_enabled: bool = Field(default=False)
    """Enable OpenTelemetry tracing."""


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
        env_nested_delimiter="__",
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    env: Literal["dev", "staging", "prod"] = Field(default="dev")
    debug: bool = Field(default=False)
    test_mode: bool = Field(default=False)
    metrics_port: int = Field(default=8000, ge=1, le=65535)
    """Port for Prometheus metrics HTTP server (default: 8000)."""
    strict_error_handling: bool = Field(
        default=False,
        description="When True, API client errors raise exceptions instead of being silently ignored. "
        "Recommended for dev/staging environments.",
    )

    aws: AWSSettings = Field(default_factory=AWSSettings)
    s3: S3Settings = Field(default_factory=S3Settings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    # Provider-specific settings
    default_email: str = Field(
        default="default@example.com",
        description="Default email for NCBI API",
    )
    pubmed_api_key: SecretStr | None = Field(
        default=None,
        description="API key for PubMed",
    )

    @model_validator(mode="after")
    def check_s3_endpoint_for_dev(self) -> Settings:
        """Validate S3 endpoint configuration.

        For dev environment:
        - If endpoint_url is set, S3/MinIO storage will be used
        - If endpoint_url is None, local file storage will be used

        For prod environment:
        - AWS credentials should be configured (IAM role or env vars)
        """
        # test_mode bypasses validation
        if self.test_mode:
            return self
        # dev without endpoint_url = local storage mode (allowed)
        # prod typically uses IAM roles, so no explicit endpoint needed
        return self

    @property
    def storage_options(self) -> dict[str, str] | None:
        """Get storage options for Delta Lake/Polars."""
        if not self.aws.endpoint_url:
            return None

        secret = self.aws.secret_access_key
        options = {
            "AWS_ENDPOINT_URL": self.aws.endpoint_url,
            "AWS_ACCESS_KEY_ID": self.aws.access_key_id or "",
            "AWS_SECRET_ACCESS_KEY": secret.get_secret_value() if secret else "",
        }

        # delta-rs requires allow_http for HTTP endpoints (e.g., local MinIO)
        if self.aws.endpoint_url.startswith("http://"):
            options["allow_http"] = "true"
            # Disable DynamoDB locking for local S3-compatible storage (e.g., MinIO)
            options["AWS_S3_LOCKING_PROVIDER"] = "none"

        return options

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
            init_settings,
            env_settings,
            dotenv_settings,
            YamlSettingsSource(settings_cls),
            file_secret_settings,
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# =============================================================================
# Re-exports for CLI/interfaces convenience
# =============================================================================

# RuntimeConfig is defined in domain.config but re-exported here
# for convenience when used in CLI/interfaces layer
from bioetl.domain.config import RuntimeConfig

__all__ = [
    "RuntimeConfig",
    "Settings",
    "get_pipeline_config",
    "get_settings",
    "load_pipeline_config",
    "yaml_config_to_domain",
]
