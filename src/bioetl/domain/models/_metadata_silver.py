# mypy: disable-error-code="misc"
"""Silver layer metadata models.

Contains lineage tracking, Delta Lake metrics, data quality models,
and the complete SilverMetadata aggregate for sidecar files.
LineageMetadata and DQSummary are also used by Gold layer.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from bioetl.domain.medallion import Layer
from bioetl.domain.models._metadata_common import (
    BaseOutputMetadata,
    EnvironmentMetadata,
    GovernanceMetadata,
    PipelineMetadata,
    RuntimeMetadata,
)

__all__ = [
    "ColumnMetrics",
    "DQSummary",
    "DeltaMetrics",
    "LineageMetadata",
    "SchemaDrift",
    "SilverMetadata",
    "SilverOutputExt",
]


class LineageMetadata(BaseModel):
    """Lineage information for Silver/Gold layers.

    Attributes:
        source_batch_ids: List of source batch UUIDs.
        bronze_paths: List of Bronze file paths.
        transform_version: Version of transform applied.
        transform_steps: List of transform steps applied.
        source_tables: Source tables for Gold layer (table name -> version).
    """

    source_batch_ids: list[str] = Field(
        default_factory=list, description="Source batch UUIDs"
    )
    bronze_paths: list[str] = Field(
        default_factory=list, description="Source Bronze file paths"
    )
    transform_version: str | None = Field(default=None, description="Transform version")
    transform_steps: list[str] = Field(
        default_factory=list, description="Transform steps applied"
    )
    source_tables: dict[str, int] = Field(
        default_factory=dict, description="Source tables with Delta versions"
    )


class DeltaMetrics(BaseModel):
    """Delta Lake operation metrics.

    Attributes:
        table_path: Delta table path.
        operation: Delta operation (merge, overwrite, append).
        primary_key: Primary key columns.
        partition_by: Partition columns.
        version_before: Delta version before write.
        version_after: Delta version after write.
        files_added: Number of files added.
        files_removed: Number of files removed.
        rows_inserted: Number of rows inserted.
        rows_updated: Number of rows updated.
        rows_deleted: Number of rows deleted.
    """

    table_path: str = Field(description="Delta table path")
    operation: Literal["merge", "overwrite", "append"] = Field(
        description="Delta operation"
    )
    primary_key: list[str] = Field(default_factory=list, description="Primary key")
    partition_by: list[str] = Field(
        default_factory=list, description="Partition columns"
    )
    version_before: int | None = Field(default=None, description="Version before write")
    version_after: int | None = Field(default=None, description="Version after write")
    files_added: int = Field(default=0, description="Files added")
    files_removed: int = Field(default=0, description="Files removed")
    rows_inserted: int = Field(default=0, description="Rows inserted")
    rows_updated: int = Field(default=0, description="Rows updated")
    rows_deleted: int = Field(default=0, description="Rows deleted")


class ColumnMetrics(BaseModel):
    """Per-column data quality metrics.

    Attributes:
        null_rate: Fraction of null values (0.0-1.0).
        unique_count: Number of unique values.
        min: Minimum value (for numeric columns).
        max: Maximum value (for numeric columns).
        mean: Mean value (for numeric columns).
    """

    null_rate: float = Field(default=0.0, description="Null rate (0.0-1.0)")
    unique_count: int | None = Field(default=None, description="Unique value count")
    min: float | None = Field(default=None, description="Minimum value")
    max: float | None = Field(default=None, description="Maximum value")
    mean: float | None = Field(default=None, description="Mean value")


class SchemaDrift(BaseModel):
    """Schema drift detection results.

    Attributes:
        status: Drift severity (info, warn, critical).
        new_fields: List of new fields detected.
        missing_fields: List of missing fields detected.
    """

    status: Literal["info", "warn", "critical"] = Field(
        default="info", description="Drift severity"
    )
    new_fields: list[str] = Field(default_factory=list, description="New fields")
    missing_fields: list[str] = Field(
        default_factory=list, description="Missing fields"
    )


class DQSummary(BaseModel):
    """Data quality summary metrics.

    Attributes:
        total_records: Total records processed.
        valid_records: Records passing validation.
        error_records: Records sent to quarantine.
        warning_records: Records with warnings.
        error_rate: Error rate (0.0-1.0).
        column_metrics: Per-column metrics.
        schema_drift: Schema drift detection.
        validation_passed: Whether DQ validation passed.
        data_freshness_hours: Data freshness in hours.
    """

    total_records: int = Field(default=0, description="Total records")
    valid_records: int = Field(default=0, description="Valid records")
    error_records: int = Field(default=0, description="Error records (quarantined)")
    warning_records: int = Field(default=0, description="Warning records")
    error_rate: float = Field(default=0.0, description="Error rate")
    column_metrics: dict[str, ColumnMetrics] = Field(
        default_factory=dict, description="Per-column metrics"
    )
    schema_drift: SchemaDrift | None = Field(
        default=None, description="Schema drift info"
    )
    validation_passed: bool = Field(default=True, description="DQ validation passed")
    data_freshness_hours: float | None = Field(
        default=None, description="Data freshness in hours"
    )
    rule_provenance: list[dict[str, str | None]] = Field(
        default_factory=list,
        description=(
            "DQ rule provenance entries with rule_id, config_path, layer, "
            "field, severity, and decision"
        ),
    )

    @property
    def null_rates(self) -> dict[str, float]:
        """Get null rates for all columns."""
        return {col: metrics.null_rate for col, metrics in self.column_metrics.items()}


class SilverOutputExt(BaseModel):
    """Silver-specific output metadata extension.

    Tracks Delta Lake versioning for merge operations.

    Attributes:
        delta_version_before: Delta table version before write.
        delta_version_after: Delta table version after write.
    """

    delta_version_before: int | None = Field(
        default=None,
        description="Delta table version before write",
    )
    delta_version_after: int | None = Field(
        default=None,
        description="Delta table version after write",
    )


class SilverMetadata(BaseModel):
    """Complete metadata for Silver layer sidecar file.

    Includes lineage tracking from Bronze, DQ metrics, and governance metadata.

    ADR-029: Uses unified BaseOutputMetadata + SilverOutputExt composition.
    """

    version: str = Field(default="1.1", description="Metadata schema version")
    layer: Layer = Field(default=Layer.SILVER, description="Medallion layer")
    runtime: RuntimeMetadata = Field(description="Runtime context")
    pipeline: PipelineMetadata = Field(description="Pipeline identification")
    lineage: LineageMetadata = Field(
        default_factory=LineageMetadata, description="Lineage information"
    )
    delta: DeltaMetrics = Field(description="Delta Lake metrics")
    dq_summary: DQSummary = Field(
        default_factory=DQSummary, description="Data quality summary"
    )
    output: BaseOutputMetadata = Field(
        default_factory=BaseOutputMetadata, description="Base output metrics"
    )
    output_ext: SilverOutputExt = Field(
        default_factory=SilverOutputExt, description="Silver-specific output metrics"
    )
    environment: EnvironmentMetadata = Field(description="Environment information")
    # Cross-reference to DQ report
    dq_report_path: str | None = Field(
        default=None,
        description="Path to corresponding DQ report file (if generated)",
    )
    governance: GovernanceMetadata | None = Field(
        default=None, description="Governance metadata for data stewardship"
    )
