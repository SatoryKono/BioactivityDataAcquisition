# mypy: disable-error-code="misc,untyped-decorator"
"""Common metadata models shared across Medallion layers."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from bioetl.domain.medallion import Layer

__all__ = [
    "BaseOutputMetadata",
    "EnvironmentMetadata",
    "GovernanceLineageConfig",
    "GovernanceMetadata",
    "Layer",
    "PipelineMetadata",
    "QualityExpectations",
    "RunTypeEnum",
    "RuntimeMetadata",
    "validate_utc_datetime",
]


def validate_utc_datetime(value: datetime | None) -> datetime | None:
    """Require timezone-aware timestamps whose effective offset is UTC."""
    if value is not None and (
        value.tzinfo is None or value.utcoffset() != timedelta(0)
    ):
        raise ValueError("metadata timestamps must be timezone-aware UTC datetimes")
    return value


class RunTypeEnum(StrEnum):
    """Type of pipeline run (mirrors domain.types.RunType)."""

    INCREMENTAL = "incremental"
    BACKFILL = "backfill"
    REBUILD = "rebuild"


class GovernanceLineageConfig(BaseModel):
    """Static lineage configuration resolved from pipeline governance config."""

    source_system: str | None = Field(
        default=None, description="Source system identifier"
    )
    source_version: str | None = Field(
        default=None, description="Version of source system"
    )
    extraction_method: str | None = Field(
        default=None, description="Extraction method (api, csv, parquet)"
    )
    source_layer: str | None = Field(default=None, description="Source Medallion layer")
    transformations: list[str] = Field(
        default_factory=list, description="Transformation steps applied"
    )
    filters_applied: bool | None = Field(
        default=None, description="Whether filters were applied"
    )
    business_domain: str | None = Field(
        default=None, description="Business domain classification"
    )
    use_cases: list[str] = Field(default_factory=list, description="Intended use cases")


class QualityExpectations(BaseModel):
    """Target governance quality thresholds for a layer."""

    completeness: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Expected completeness (0-1)"
    )
    accuracy: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Expected accuracy (0-1)"
    )


class GovernanceMetadata(BaseModel):
    """Static stewardship, retention, SLA, and classification metadata."""

    owner: str | None = Field(default=None, description="Data owner")
    steward: str | None = Field(default=None, description="Data steward")
    description: str | None = Field(default=None, description="Data description")
    tags: list[str] = Field(default_factory=list, description="Classification tags")
    retention_days: int | None = Field(
        default=None, ge=1, description="Retention period in days"
    )
    sla_freshness_hours: int | None = Field(
        default=None, ge=1, description="SLA freshness in hours"
    )
    lineage: GovernanceLineageConfig = Field(
        default_factory=GovernanceLineageConfig,
        description="Static lineage configuration",
    )
    quality_expectations: QualityExpectations = Field(
        default_factory=QualityExpectations,
        description="Target quality metrics",
    )
    classification: str | None = Field(
        default=None, description="Data classification (public, internal, restricted)"
    )


class RuntimeMetadata(BaseModel):
    """Runtime execution context for one pipeline occurrence."""

    run_id: str = Field(description="Pipeline run UUID (correlation ID)")
    manifest_id: str | None = Field(
        default=None,
        description="Immutable run-manifest identifier for control-plane linkage",
    )
    run_type: RunTypeEnum = Field(description="Type of pipeline run")
    started_at_utc: datetime = Field(description="Run start timestamp (ISO 8601 UTC)")
    completed_at_utc: datetime | None = Field(
        default=None, description="Run completion timestamp"
    )
    duration_seconds: float | None = Field(
        default=None, description="Duration in seconds"
    )
    exact_replay: bool | None = Field(
        default=None,
        description="Whether this occurrence was launched in strict exact-replay mode",
    )
    replay_of_run_id: str | None = Field(
        default=None,
        description="Parent run occurrence when this run is an exact replay",
    )
    replay_of_manifest_id: str | None = Field(
        default=None,
        description="Parent manifest occurrence when this run is an exact replay",
    )
    input_snapshot_fingerprint: str | None = Field(
        default=None,
        description="Canonical input snapshot identity fingerprint for replayable runs",
    )

    @field_validator("started_at_utc", "completed_at_utc")
    @classmethod
    def _require_utc(cls, value: datetime | None) -> datetime | None:
        return validate_utc_datetime(value)


class PipelineMetadata(BaseModel):
    """Pipeline identity, versioning, and execution provenance anchors."""

    name: str = Field(description="Pipeline name")
    provider: str = Field(description="Data provider name")
    entity: str = Field(description="Entity type")
    version: str = Field(default="1.0.0", description="Pipeline version")
    git_commit: str | None = Field(default=None, description="Git commit hash")
    dependency_lock_hash: str | None = Field(
        default=None,
        description="Dependency lockfile content hash for forensic replay",
    )
    config_hash: str | None = Field(
        default=None,
        description=(
            "Legacy compatibility anchor for resolved_config_hash; new consumers "
            "must read resolved_config_hash/effective_config_hash explicitly"
        ),
    )
    resolved_config_hash: str | None = Field(
        default=None,
        description="SHA256 hash of resolved declarative pipeline config",
    )
    effective_config_hash: str | None = Field(
        default=None,
        description="Canonical effective-config hash used for semantic run identity",
    )
    effective_config_artifact_id: str | None = Field(
        default=None,
        description="Immutable effective-config artifact identifier for provenance",
    )
    execution_fingerprint: str | None = Field(
        default=None,
        description="Canonical run-manifest execution identity fingerprint",
    )
    contract_ref: str | None = Field(
        default=None,
        description="Canonical contract reference resolved for the run",
    )
    contract_version: str | None = Field(
        default=None,
        description="Resolved contract semantic version",
    )
    contract_schema_hash: str | None = Field(
        default=None,
        description="Contract schema hash from registry identity",
    )
    dq_policy_ref: str | None = Field(
        default=None,
        description="DQ policy reference aligned with the contract",
    )
    rule_bundle_version: str | None = Field(
        default=None,
        description="DQ rule-bundle version used with the contract",
    )
    normalization_profile_ref: str | None = Field(
        default=None,
        description="Normalization profile reference aligned with semantic run identity",
    )
    normalization_profile_version: str | None = Field(
        default=None,
        description="Normalization profile semantic version used during the run",
    )
    normalization_profile_hash: str | None = Field(
        default=None,
        description="Normalization profile hash used for forensic replay continuity",
    )
    dq_contract_compatibility_hash: str | None = Field(
        default=None,
        description="DQ contract compatibility hash included in execution identity",
    )


class EnvironmentMetadata(BaseModel):
    """Execution environment identity for reproducibility surfaces."""

    hostname: str = Field(description="Machine hostname")
    python_version: str = Field(description="Python version")
    bioetl_version: str = Field(description="BioETL package version")


class BaseOutputMetadata(BaseModel):
    """Shared output metadata contract for all Medallion layers."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: str | None = Field(
        default=None,
        description="Canonical output artifact identifier for sidecar/lineage linkage",
    )
    record_count: int = Field(
        default=0,
        ge=0,
        description="Total records written to layer",
    )
    total_bytes: int = Field(
        default=0,
        ge=0,
        description="Total size in bytes (compressed for Bronze, on-disk for Delta)",
    )
    content_hash: str | None = Field(
        default=None,
        description="SHA256 hash of content for change detection",
    )
    lineage_fragment_id: str | None = Field(
        default=None,
        description="Canonical lineage fragment identifier for full graph lookup",
    )
    write_started_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when write operation started",
    )
    write_completed_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when write operation completed",
    )
    composite_run_id: str | None = Field(
        default=None,
        description="Composite run identifier mapped from _composite_run_id",
    )

    @field_validator("write_started_at", "write_completed_at")
    @classmethod
    def _require_utc(cls, value: datetime | None) -> datetime | None:
        return validate_utc_datetime(value)

    @computed_field
    @property
    def write_duration_ms(self) -> int | None:
        """Calculate write duration in milliseconds when timestamps are present."""
        if self.write_started_at and self.write_completed_at:
            delta = self.write_completed_at - self.write_started_at
            return int(delta.total_seconds() * 1000)
        return None
