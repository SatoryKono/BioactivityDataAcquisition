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

from pydantic import SecretStr, field_validator, model_validator
from pydantic.fields import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from bioetl.domain.config import PipelineConfig
from bioetl.domain.constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHECKPOINT_INTERVAL,
    DEFAULT_DQ_QUALITY_SCORE_MIN,
)
from bioetl.infrastructure.config._yaml_settings_source import YamlSettingsSource
from bioetl.infrastructure.config.converters import yaml_config_to_domain
from bioetl.infrastructure.schemas.source_config import SourceYamlConfig


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

    root = Path(config_root) if config_root is not None else Path("configs")
    return load_domain_pipeline_config(
        pipeline_name,
        configs_root=root,
        relaxed_dq=False,
    )


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

    allow_noop_observability_in_prod: bool = Field(default=False)
    """Allow NoOp metrics/tracing in prod without failing bootstrap validation."""

    audit_enabled: bool = Field(default=False)
    """Enable file-backed audit logging for Medallion write operations."""

    audit_base_path: Path | None = Field(default=None)
    """Optional override path for audit JSONL files."""

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

    dq_quality_score_min: float = Field(
        default=DEFAULT_DQ_QUALITY_SCORE_MIN, ge=0.0, le=1.0
    )
    """Minimum quality score threshold (80% default)."""


class PipelineSettings(BaseSettings):
    """Pipeline execution configuration."""

    model_config = SettingsConfigDict(frozen=True)

    class ControlPlaneSettings(BaseSettings):
        """Feature flags for run manifest and ledger control-plane behavior."""

        model_config = SettingsConfigDict(frozen=True)

        required_persistence_profile: Literal[
            "degraded_observable", "replay_ready", "forensic_grade"
        ] = Field(default="degraded_observable")
        """Minimum persistence profile required for this deployment/runtime."""

        run_manifest_enabled: bool = Field(default=True)
        """When True, create immutable run manifests before execution starts."""

        run_ledger_enabled: bool = Field(default=True)
        """When True, append run-ledger events for lifecycle and lineage."""

        checkpoint_compatibility_policy: Literal[
            "observe", "legacy_observe", "soft_fail", "hard_fail"
        ] = Field(default="soft_fail")
        """Resume behavior when checkpoint compatibility validation fails.

        `observe` remains a degraded operator mode only when identity continuity
        is proven and non-identity signals drift. `legacy_observe` preserves
        the legacy degraded telemetry contract for that same non-identity drift
        path, but no longer allows resume when identity continuity is unproven.
        """

        @model_validator(mode="after")
        def _validate_ledger_dependency(self) -> PipelineSettings.ControlPlaneSettings:
            """Ledger requires manifest creation because it is keyed by manifest_id."""
            if self.run_ledger_enabled and not self.run_manifest_enabled:
                raise ValueError(
                    "pipeline.control_plane.run_ledger_enabled requires "
                    "pipeline.control_plane.run_manifest_enabled"
                )
            if (
                self.required_persistence_profile in {"replay_ready", "forensic_grade"}
                and not self.run_manifest_enabled
            ):
                raise ValueError(
                    "pipeline.control_plane.required_persistence_profile="
                    f"{self.required_persistence_profile} requires "
                    "pipeline.control_plane.run_manifest_enabled"
                )
            if (
                self.required_persistence_profile == "forensic_grade"
                and not self.run_ledger_enabled
            ):
                raise ValueError(
                    "pipeline.control_plane.required_persistence_profile="
                    "forensic_grade requires "
                    "pipeline.control_plane.run_ledger_enabled"
                )
            if self.required_persistence_profile in {
                "replay_ready",
                "forensic_grade",
            } and self.checkpoint_compatibility_policy in {"observe", "legacy_observe"}:
                raise ValueError(
                    "pipeline.control_plane.required_persistence_profile="
                    f"{self.required_persistence_profile} requires "
                    "pipeline.control_plane.checkpoint_compatibility_policy "
                    "to be soft_fail or hard_fail"
                )
            return self

    class AtomicReplaceRetrySettings(BaseSettings):
        """Atomic ``Path.replace`` retry policy for metadata sidecars."""

        model_config = SettingsConfigDict(frozen=True)

        enabled: bool = Field(default=True)
        adaptive_backoff: bool = Field(default=True)
        max_retries: int = Field(default=20, ge=0, le=30)
        base_delay_seconds: float = Field(default=0.010, ge=0.0, le=5.0)
        max_delay_seconds: float = Field(default=0.250, ge=0.0, le=10.0)
        jitter_seconds: float = Field(default=0.010, ge=0.0, le=1.0)

    class SilverMergeRetrySettings(BaseSettings):
        """Retry policy for Delta commit conflict retries in Silver merge."""

        model_config = SettingsConfigDict(frozen=True)

        enabled: bool = Field(default=True)
        adaptive_backoff: bool = Field(default=True)
        max_retries: int = Field(default=3, ge=0, le=20)
        base_delay_seconds: float = Field(default=0.250, ge=0.0, le=30.0)
        max_delay_seconds: float = Field(default=2.0, ge=0.0, le=60.0)
        jitter_seconds: float = Field(default=0.050, ge=0.0, le=5.0)

    class SilverMergeTimeoutSettings(BaseSettings):
        """Timeout and retry policy for Delta merge execution in Silver."""

        model_config = SettingsConfigDict(frozen=True)

        profile: Literal["default", "unit", "e2e"] = Field(default="default")
        execution_timeout_seconds: float = Field(default=45.0, ge=1.0, le=600.0)
        unit_execution_timeout_seconds: float = Field(default=15.0, ge=1.0, le=600.0)
        e2e_execution_timeout_seconds: float = Field(default=90.0, ge=1.0, le=600.0)
        retry_enabled: bool = Field(default=True)
        adaptive_backoff: bool = Field(default=True)
        max_retries: int = Field(default=1, ge=0, le=10)
        base_delay_seconds: float = Field(default=0.200, ge=0.0, le=30.0)
        max_delay_seconds: float = Field(default=2.0, ge=0.0, le=60.0)
        jitter_seconds: float = Field(default=0.050, ge=0.0, le=5.0)

    batch_size: int = Field(default=DEFAULT_BATCH_SIZE, ge=1, le=10000)
    """Number of records per batch write."""

    checkpoint_interval: int = Field(default=DEFAULT_CHECKPOINT_INTERVAL, ge=100)
    """Save checkpoint every N records."""

    relaxed_dq: bool = Field(default=False)
    """When True, DQ thresholds are relaxed (soft=0.99, hard=1.0) for testing."""

    max_concurrent_batches: int = Field(default=4, ge=1, le=16)
    """Maximum concurrent batch writes."""

    heartbeat_interval: int = Field(default=30, ge=5, le=60)
    """Lock heartbeat interval in seconds (default: 30s, range: 5-60s)."""

    silver_resilience_enabled: bool = Field(default=True)
    """Feature flag for adaptive resilience in Silver merge and metadata writes."""

    silver_metadata_atomic_retry: AtomicReplaceRetrySettings = Field(
        default_factory=AtomicReplaceRetrySettings
    )
    """Atomic replace retry policy for Silver metadata sidecars."""

    silver_merge_retry: SilverMergeRetrySettings = Field(
        default_factory=SilverMergeRetrySettings
    )
    """Commit conflict retry policy for Delta merge operations."""

    silver_merge_timeout: SilverMergeTimeoutSettings = Field(
        default_factory=SilverMergeTimeoutSettings
    )
    """Delta merge execution timeout policy with dedicated retry controls."""

    health_check_mode: Literal["strict", "probe"] = Field(default="strict")
    """Preflight health-check gate mode: strict blocks on UNHEALTHY, probe degrades."""

    control_plane: ControlPlaneSettings = Field(default_factory=ControlPlaneSettings)
    """Feature flags controlling RunManifest and RunLedger rollout behavior."""


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
        description="Whether salt rotation is active (BIOETL_SALT_ROTATION_ACTIVE)",
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
    openalex_api_key: SecretStr | None = Field(
        default=None,
        description="API key for OpenAlex",
    )

    @field_validator("silver_dedup_timeout_seconds", mode="before")
    @classmethod
    def _validate_silver_dedup_timeout_seconds(cls, value: object) -> float:
        """Coerce invalid or non-positive timeout values back to the safe default."""
        if value is None or value == "":
            return 60.0
        if isinstance(value, bool):
            return 60.0
        if isinstance(value, (int, float, str)):
            parsed = float(value)
            return parsed if parsed > 0 else 60.0
        return 60.0

    semanticscholar_api_key: SecretStr | None = Field(
        default=None,
        description="API key for Semantic Scholar Academic Graph API",
    )

    @property
    def bronze_path(self) -> Path:
        """Path for Bronze layer storage."""
        return self.data_dir / "output" / "bronze"

    @property
    def silver_path(self) -> Path:
        """Path for Silver layer storage."""
        return self.data_dir / "output" / "silver"

    @property
    def gold_path(self) -> Path:
        """Path for Gold layer storage."""
        return self.data_dir / "output" / "gold"

    @property
    def checkpoint_path(self) -> Path:
        """Path for checkpoint storage."""
        return self.data_dir / "output" / "checkpoints"

    @property
    def quarantine_path(self) -> Path:
        """Path for quarantine storage."""
        return self.data_dir / "output" / "quarantine"

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
