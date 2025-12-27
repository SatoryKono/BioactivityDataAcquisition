"""Centralized configuration for BioETL.

Uses pydantic-settings for type-safe, validated configuration from environment
variables and YAML files. All settings are loaded once at startup and validated.

Consolidated configuration (post-refactoring):
- Settings: Main application settings (pydantic-settings)
- RuntimeConfig: Re-exported from domain.config for CLI convenience

Usage:
    from bioetl.infrastructure.config import get_settings

    settings = get_settings()
    print(settings.data_dir)
    print(settings.pipeline.batch_size)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import SecretStr
from pydantic.fields import Field, FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.config import PipelineConfig
from bioetl.domain.filter_config import (
    GoldColumnFilter,
    GoldFilterConfig,
    GoldListContainsFilter,
    GoldListLengthFilter,
    GoldRangeFilter,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class YamlSettingsSource(PydanticBaseSettingsSource):
    """A settings source that loads variables from a YAML file."""

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        """Get value of a field from YAML file."""
        encoding = self.config.get("env_file_encoding")
        try:
            with Path("config.yaml").open(encoding=encoding) as f:
                file_content = yaml.safe_load(f)
        except FileNotFoundError:
            return None, field_name, False

        if not isinstance(file_content, dict):
            return None, field_name, False

        field_value = file_content.get(field_name)
        return field_value, field_name, False

    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        """Prepare value of a field."""
        return value

    def __call__(self) -> dict[str, Any]:
        d: dict[str, Any] = {}

        for field_name, field in self.settings_cls.model_fields.items():
            field_value, field_key, value_is_complex = self.get_field_value(
                field, field_name
            )
            if field_value is not None:
                field_value = self.prepare_field_value(
                    field_name, field, field_value, value_is_complex
                )
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
    validated: PipelineYamlConfig = PipelineYamlConfig.model_validate(config)
    return validated


def _extract_source_fields(yaml_config: PipelineYamlConfig) -> list[str]:
    """Extract field names from source config."""
    source_fields = yaml_config.source.fields
    if source_fields and isinstance(source_fields[0], dict):
        return [field["name"] for field in source_fields if "name" in field]
    return source_fields  # type: ignore[return-value]


def _extract_write_modes(
    yaml_config: PipelineYamlConfig,
) -> tuple[Literal["merge", "append", "overwrite"], Literal["append", "overwrite", "scd2"]]:
    """Extract write modes from sink config."""
    silver_config = yaml_config.sink.get("silver")
    gold_config = yaml_config.sink.get("gold")

    write_mode: Literal["merge", "append", "overwrite"] = "merge"
    if silver_config and silver_config.mode:
        # Cast the mode string to the literal type
        write_mode = silver_config.mode  # type: ignore[assignment]

    gold_write_mode: Literal["append", "overwrite", "scd2"] = "append"
    if gold_config and gold_config.mode:
        # Cast the mode string to the literal type
        gold_write_mode = gold_config.mode  # type: ignore[assignment]

    return write_mode, gold_write_mode


def _build_gold_filters(yaml_config: PipelineYamlConfig) -> GoldFilterConfig:
    """Build GoldFilterConfig from YAML config."""
    gf = yaml_config.gold_filters
    return GoldFilterConfig(
        column_filters=tuple(
            GoldColumnFilter(column=col, values=frozenset(vals))
            for col, vals in gf.columns.items()
        ),
        range_filters=tuple(
            GoldRangeFilter(
                column=col,
                min_value=r.min,
                max_value=r.max,
                include_min=r.include_min,
                include_max=r.include_max,
            )
            for col, r in gf.ranges.items()
        ),
        list_length_filters=tuple(
            GoldListLengthFilter(column=col, min_length=r.min, max_length=r.max)
            for col, r in gf.list_lengths.items()
        ),
        list_contains_filters=tuple(
            GoldListContainsFilter(column=col, values=frozenset(r.values), mode=r.mode)
            for col, r in gf.list_contains.items()
        ),
        required_fields=tuple(gf.required_fields),
        exclude_if_present=tuple(gf.exclude_if_present),
    )


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
    source_fields = _extract_source_fields(yaml_config)
    write_mode, gold_write_mode = _extract_write_modes(yaml_config)
    gold_filters = _build_gold_filters(yaml_config)

    # Extract on_schema_mismatch from silver sink config
    on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error"
    if yaml_config.sink:
        silver_sink = yaml_config.sink.get("silver")
        if silver_sink:
            on_schema_mismatch = silver_sink.on_schema_mismatch

    return PipelineConfig(
        pipeline_name=yaml_config.pipeline_name,
        provider=yaml_config.provider,
        entity_type=yaml_config.entity_type,
        primary_keys=tuple(yaml_config.primary_keys),
        silver_table=yaml_config.silver_table,
        gold_table=yaml_config.gold_table,
        write_mode=write_mode,
        gold_write_mode=gold_write_mode,
        gold_filters=gold_filters,
        batch_size=yaml_config.batch_size,
        checkpoint_interval=yaml_config.checkpoint_interval,
        fields=tuple(source_fields),
        dq=DomainDQConfig(
            soft_fail_threshold=yaml_config.dq_rules.soft_fail_threshold,
            hard_fail_threshold=yaml_config.dq_rules.hard_fail_threshold,
        ),
        on_schema_mismatch=on_schema_mismatch,
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


class ObservabilitySettings(BaseSettings):
    """Observability configuration."""

    model_config = SettingsConfigDict(frozen=True)

    metrics_enabled: bool = Field(default=True)
    """Enable metrics collection."""

    metrics_server_enabled: bool = Field(default=True)
    """Enable Prometheus metrics HTTP server. Requires metrics_enabled=True."""

    metrics_fail_fast: bool = Field(default=False)
    """If True, exit with error when metrics server fails to start."""

    metrics_retry_count: int = Field(default=3, ge=1, le=10)
    """Number of retries for transient errors when starting metrics server."""

    metrics_retry_delay: float = Field(default=1.0, ge=0.1, le=10.0)
    """Delay between retries in seconds when starting metrics server."""

    tracing_enabled: bool = Field(default=False)
    """Enable OpenTelemetry tracing."""

    # Data Quality Monitor settings
    dq_monitor_enabled: bool = Field(default=False)
    """Enable data quality monitoring. Disabled by default."""

    dq_baseline_window: int = Field(default=7, ge=1, le=30)
    """Number of recent runs to use for baseline calculation."""

    dq_z_score_threshold: float = Field(default=2.5, ge=1.5, le=5.0)
    """Z-score threshold for anomaly detection."""

    dq_min_baseline_samples: int = Field(default=3, ge=1, le=10)
    """Minimum samples before anomaly detection activates."""

    dq_cold_start_runs: int = Field(default=5, ge=0, le=20)
    """Skip first N runs while building baseline."""

    dq_error_rate_max: float = Field(default=0.10, ge=0.0, le=1.0)
    """Maximum allowed error rate (10% default)."""

    dq_quality_score_min: float = Field(default=0.80, ge=0.0, le=1.0)
    """Minimum quality score threshold (80% default)."""


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

    # Provider-specific settings
    default_email: str = Field(
        default="default@example.com",
        description="Default email for NCBI API",
    )
    pubmed_api_key: SecretStr | None = Field(
        default=None,
        description="API key for PubMed",
    )

    @property
    def bronze_path(self) -> Path:
        """Path for Bronze layer storage."""
        return self.data_dir / "bronze"

    @property
    def silver_path(self) -> Path:
        """Path for Silver layer storage."""
        return self.data_dir / "silver"

    @property
    def gold_path(self) -> Path:
        """Path for Gold layer storage."""
        return self.data_dir / "gold"

    @property
    def checkpoint_path(self) -> Path:
        """Path for checkpoint storage."""
        return self.data_dir / "checkpoints"

    @property
    def quarantine_path(self) -> Path:
        """Path for quarantine storage."""
        return self.data_dir / "quarantine"

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
    """Get cached application settings."""
    return Settings()


# =============================================================================
# Re-exports for CLI/interfaces convenience
# =============================================================================

# RuntimeConfig is defined in domain.config but re-exported here
# for convenience when used in CLI/interfaces layer
from bioetl.domain.config import RuntimeConfig  # noqa: E402

__all__ = [
    "RuntimeConfig",
    "Settings",
    "get_pipeline_config",
    "get_settings",
    "load_pipeline_config",
    "yaml_config_to_domain",
]
