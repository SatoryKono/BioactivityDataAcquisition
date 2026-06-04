"""Pipeline execution configuration settings."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from bioetl.domain.constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHECKPOINT_INTERVAL,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)

from ._retry_settings import (
    AtomicReplaceRetrySettings,
    SilverMergeRetrySettings,
    SilverMergeTimeoutSettings,
)


class ControlPlaneSettings(BaseSettings):
    """Feature flags for run manifest and ledger control-plane behavior."""

    model_config = SettingsConfigDict(frozen=True)

    required_persistence_profile: Literal[
        "degraded_observable", "replay_ready", "forensic_grade"
    ] = Field(default="replay_ready")
    """Minimum persistence profile required for this deployment/runtime."""

    run_manifest_enabled: bool = Field(default=True)
    """When True, create immutable run manifests before execution starts."""

    run_ledger_enabled: bool = Field(default=True)
    """When True, append run-ledger events for lifecycle and lineage."""

    checkpoint_compatibility_policy: Literal["observe", "soft_fail", "hard_fail"] = (
        Field(default="hard_fail")
    )
    """Resume behavior when checkpoint compatibility validation fails.

    `observe` remains a degraded operator mode only when identity continuity
    is proven and non-identity signals drift.
    """

    @model_validator(mode="after")
    def _validate_ledger_dependency(self) -> ControlPlaneSettings:
        """Ledger requires manifest creation because it is keyed by manifest_id."""
        if self.run_ledger_enabled and not self.run_manifest_enabled:
            raise ValueError(
                "pipeline.control_plane.run_ledger_enabled requires "
                "pipeline.control_plane.run_manifest_enabled"
            )
        if (
            self.required_persistence_profile in STRICT_PERSISTENCE_PROFILES
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
        if (
            self.required_persistence_profile in STRICT_PERSISTENCE_PROFILES
            and self.checkpoint_compatibility_policy != "hard_fail"
        ):
            raise ValueError(
                "pipeline.control_plane.required_persistence_profile="
                f"{self.required_persistence_profile} requires "
                "pipeline.control_plane.checkpoint_compatibility_policy "
                "to be hard_fail"
            )
        return self


class PipelineSettings(BaseSettings):
    """Pipeline execution configuration."""

    model_config = SettingsConfigDict(frozen=True)

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
