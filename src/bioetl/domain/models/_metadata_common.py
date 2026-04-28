# mypy: disable-error-code="misc,untyped-decorator"
"""Common metadata models shared across Medallion layers."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field

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
]


class RunTypeEnum(StrEnum):
    """Type of pipeline run (mirrors domain.types.RunType)."""

    INCREMENTAL = "incremental"
    BACKFILL = "backfill"
    REBUILD = "rebuild"


class GovernanceLineageConfig(BaseModel):
    """Governance-level lineage configuration from pipeline config.

    Captures static lineage information defined in pipeline YAML,
    separate from runtime lineage tracked in LineageMetadata.

    Attributes:
        source_system: Source system identifier (e.g., "chembl", "pubchem").
        source_version: Version of source system/API.
        extraction_method: How data was extracted (api, csv, parquet).
        source_layer: Source Medallion layer (for Silver/Gold).
        transformations: List of transformation steps applied.
        filters_applied: Whether Gold filters were applied.
        business_domain: Business domain classification.
        use_cases: Intended use cases for the data.
    """

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
    """Quality expectations for data governance.

    Defines target quality metrics for the data layer.

    Attributes:
        completeness: Expected completeness rate (0.0-1.0).
        accuracy: Expected accuracy rate (0.0-1.0).
    """

    completeness: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Expected completeness (0-1)"
    )
    accuracy: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Expected accuracy (0-1)"
    )


class GovernanceMetadata(BaseModel):
    """Governance metadata for data stewardship and compliance.

    Captures static governance information from pipeline configuration
    that describes data ownership, retention, and SLA requirements.
    This is separate from execution metadata (runtime, DQ metrics, etc.).

    Attributes:
        owner: Data owner team or individual.
        steward: Data steward responsible for quality.
        description: Human-readable description of the data.
        tags: Classification tags for discovery.
        retention_days: Data retention period in days.
        sla_freshness_hours: SLA for data freshness in hours.
        lineage: Static lineage configuration from pipeline config.
        quality_expectations: Target quality metrics.
        classification: Data classification level (public, internal, restricted).
    """

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
    """Runtime execution context.

    Attributes:
        run_id: Unique pipeline run identifier (UUID).
        manifest_id: Immutable control-plane manifest identifier for the run.
        run_type: Type of pipeline run.
        started_at_utc: UTC timestamp when run started.
        completed_at_utc: UTC timestamp when run completed.
        duration_seconds: Total duration of the operation.
    """

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


class PipelineMetadata(BaseModel):
    """Pipeline identification and versioning.

    Attributes:
        name: Pipeline name (e.g., 'chembl_activity').
        provider: Data provider name (e.g., 'chembl').
        entity: Entity type (e.g., 'activity').
        version: Pipeline/transform version.
        git_commit: Git commit hash for reproducibility.
        config_hash: Legacy compatibility anchor for the resolved config hash.
        resolved_config_hash: SHA256 hash of resolved declarative config.
        effective_config_hash: SHA256 hash of final effective execution config.
    """

    name: str = Field(description="Pipeline name")
    provider: str = Field(description="Data provider name")
    entity: str = Field(description="Entity type")
    version: str = Field(default="1.0.0", description="Pipeline version")
    git_commit: str | None = Field(default=None, description="Git commit hash")
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
    dq_contract_compatibility_hash: str | None = Field(
        default=None,
        description="DQ contract compatibility hash included in execution identity",
    )


class EnvironmentMetadata(BaseModel):
    """Execution environment information.

    Attributes:
        hostname: Machine hostname.
        python_version: Python version.
        bioetl_version: BioETL package version.
    """

    hostname: str = Field(description="Machine hostname")
    python_version: str = Field(description="Python version")
    bioetl_version: str = Field(description="BioETL package version")


class BaseOutputMetadata(BaseModel):
    """Base output metadata contract for all Medallion layers.

    Provides common fields required for downstream analytics,
    monitoring, and data lineage tracking. All layer-specific
    output metadata classes use this as the common output field.

    ADR-029: Output metadata unification.

    Attributes:
        artifact_id: Canonical output artifact identifier for the sidecar payload.
        record_count: Total records written to layer.
        total_bytes: Total size in bytes (compressed for Bronze, on-disk for Delta).
        content_hash: SHA256 hash of content for change detection.
        lineage_fragment_id: Canonical lineage fragment identifier for full graph lookup.
        write_started_at: UTC timestamp when write operation started.
        write_completed_at: UTC timestamp when write operation completed.
    """

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

    @computed_field
    @property
    def write_duration_ms(self) -> int | None:
        """Calculate write duration in milliseconds when timestamps are present."""
        if self.write_started_at and self.write_completed_at:
            delta = self.write_completed_at - self.write_started_at
            return int(delta.total_seconds() * 1000)
        return None
