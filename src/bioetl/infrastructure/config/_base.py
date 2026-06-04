# mypy: disable-error-code="misc,untyped-decorator"
"""Centralized configuration for BioETL.

Uses pydantic-settings for type-safe, validated configuration from environment
variables and YAML files. All settings are loaded once at startup and validated.

Consolidated configuration (post-refactoring):
- Settings: Main application settings (pydantic-settings)
- RuntimeConfig: Re-exported from domain.config for CLI convenience

Usage:
    >>> from bioetl.infrastructure.config import get_settings
    >>> settings = get_settings()
    >>> settings.data_dir  # doctest: +ELLIPSIS
    ...Path('data')
    >>> settings.pipeline.batch_size
    100
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic.fields import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from bioetl.domain.config import PipelineConfig
from bioetl.infrastructure.config._observability_settings import ObservabilitySettings
from bioetl.infrastructure.config._path_settings import StoragePathSettingsMixin
from bioetl.infrastructure.config._pipeline_settings import PipelineSettings
from bioetl.infrastructure.config._settings_validation import (
    coerce_silver_dedup_timeout_seconds,
)
from bioetl.infrastructure.config._yaml_settings_source import YamlSettingsSource
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.config.converters import yaml_config_to_domain
from bioetl.infrastructure.schemas.source_config import SourceYamlConfig


def _get_pipeline_config_root(config_root: str | None) -> Path:
    """Resolve helper config root without implicit cwd-sensitive overrides."""
    if config_root is not None:
        return resolve_configs_root(Path(config_root))
    return resolve_configs_root()


@lru_cache(maxsize=10)
def get_pipeline_config(
    pipeline_name: str,
    config_root: str | None = None,
) -> PipelineConfig:
    """Get PipelineConfig object from YAML configuration.

    Convenience function that loads and maps config in one step.
    Results are cached for efficiency.

    Uses the canonical function-based domain-config bridge to combine validated
    YAML config with hierarchical DQ resolution from infrastructure config
    loaders.

    Args:
        pipeline_name: Name of the pipeline (e.g., 'chembl_activity')
        config_root: Root directory for config files. Defaults to 'configs'.
            Accepts str instead of Path because lru_cache requires hashable args.

    Returns:
        PipelineConfig instance

    Raises:
        ValueError: If pipeline configuration not found

    """
    from bioetl.infrastructure.config.domain_config_resolver import (
        load_domain_pipeline_config,
    )

    root = _get_pipeline_config_root(config_root)
    return load_domain_pipeline_config(
        pipeline_name,
        configs_root=root,
        relaxed_dq=False,
    )


class Settings(StoragePathSettingsMixin, BaseSettings):
    """Main application settings for local deployment."""

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
    metrics_enabled: bool = Field(default=True)
    metrics_port: int = Field(default=8000, ge=1, le=65535)
    """Port for Prometheus metrics HTTP server (default: 8000)."""
    metrics_addr: str = Field(default="0.0.0.0")
    """Address to bind Prometheus metrics HTTP server (default: 0.0.0.0)."""
    silver_dedup_timeout_seconds: float = Field(
        default=60.0,
        validation_alias="BIOETL_SILVER_DEDUP_TIMEOUT_SECONDS",
        description=(
            "Timeout budget in seconds for Silver deduplication executor work "
            "(BIOETL_SILVER_DEDUP_TIMEOUT_SECONDS)"
        ),
    )
    """Timeout budget in seconds for Silver deduplication work."""
    strict_error_handling: bool = Field(
        default=False,
        description="When True, API client errors raise exceptions instead of being silently ignored. "
        "Recommended for dev/staging environments.",
    )
    strict_medallion: bool = Field(
        default=False,
        description="When True, schema drift in Silver layer raises SchemaEvolutionError. "
        "When False (default), schema drift is handled per pipeline config. "
        "Set via BIOETL_STRICT_MEDALLION=true for stricter validation.",
    )

    # Local storage paths
    data_dir: Path = Field(default=Path("data"))
    """Base directory for all data storage (bronze, silver, gold, checkpoints)."""

    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    # Security settings (PII hashing)
    pii_salt_current: SecretStr | None = Field(
        default=None,
        description="Current salt for PII hashing (BIOETL_PII_SALT_CURRENT)",
    )
    pii_salt_next: SecretStr | None = Field(
        default=None,
        description="Next salt for rotation (BIOETL_PII_SALT_NEXT)",
    )
    pii_salt_rotation_active: bool = Field(
        default=False,
        description="Whether salt rotation is active (BIOETL_PII_SALT_ROTATION_ACTIVE)",
    )

    # Serialization settings
    json_encoder: Literal["orjson", "stdlib", ""] = Field(
        default="",
        description="JSON encoder implementation (orjson or stdlib) (BIOETL_JSON_ENCODER)",
    )

    # Provider-specific settings
    # NOTE: default_email is NOT PII (Personally Identifiable Information).
    # It is a technical API identifier required by NCBI E-utilities for
    # tool identification and rate limit management, not user personal data.
    # See: https://www.ncbi.nlm.nih.gov/books/NBK25497/#chapter2.Usage_Guidelines_and_Requiremen
    default_email: str = Field(
        default="default@example.com",
        description="Technical email for NCBI API tool identification (NOT user PII)",
    )
    pubmed_api_key: SecretStr | None = Field(
        default=None,
        description="API key for PubMed",
    )
    uniprot_api_key: SecretStr | None = Field(
        default=None,
        description="Optional API key for UniProt higher-throughput access",
    )
    openalex_api_key: SecretStr | None = Field(
        default=None,
        description="API key for OpenAlex",
    )

    @field_validator("silver_dedup_timeout_seconds", mode="before")
    @classmethod
    def _validate_silver_dedup_timeout_seconds(cls, value: object) -> float:
        """Coerce invalid or non-positive timeout values back to the safe default."""
        return coerce_silver_dedup_timeout_seconds(value)

    semanticscholar_api_key: SecretStr | None = Field(
        default=None,
        description="API key for Semantic Scholar Academic Graph API",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customise Pydantic settings sources to include YAML.

        Args:
            settings_cls: Settings class.
            init_settings: Init settings source.
            env_settings: Env settings source.
            dotenv_settings: Dotenv settings source.
            file_secret_settings: File secret settings source.

        Returns:
            Tuple of settings sources with YamlSettingsSource prepended.

        """
        return (
            YamlSettingsSource(settings_cls),
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Settings.
    """
    return Settings()


__all__ = [
    "Settings",
    "SourceYamlConfig",
    "get_pipeline_config",
    "get_settings",
    "yaml_config_to_domain",
]
