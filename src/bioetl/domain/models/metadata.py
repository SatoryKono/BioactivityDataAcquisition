"""Metadata models for Medallion layer sidecar files.

Defines Pydantic models for _metadata.yaml files that accompany
data artifacts in Bronze, Silver, and Gold layers.

Implements RULES.md 2.3 and 02-user-rules.md 2.4:
- Lineage tracking
- QC information
- Runtime context

Version: 1.0
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LayerType(str, Enum):
    """Medallion architecture layer type."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class RunTypeEnum(str, Enum):
    """Type of pipeline run (mirrors domain.types.RunType)."""

    INCREMENTAL = "incremental"
    BACKFILL = "backfill"
    REBUILD = "rebuild"


# =============================================================================
# Governance Metadata Components
# =============================================================================


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


# =============================================================================
# Common Components
# =============================================================================


class RuntimeMetadata(BaseModel):
    """Runtime execution context.

    Attributes:
        run_id: Unique pipeline run identifier (UUID).
        run_type: Type of pipeline run.
        started_at_utc: UTC timestamp when run started.
        completed_at_utc: UTC timestamp when run completed.
        duration_seconds: Total duration of the operation.
    """

    run_id: str = Field(description="Pipeline run UUID (correlation ID)")
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
        config_hash: SHA256 hash of pipeline config.
    """

    name: str = Field(description="Pipeline name")
    provider: str = Field(description="Data provider name")
    entity: str = Field(description="Entity type")
    version: str = Field(default="1.0.0", description="Pipeline version")
    git_commit: str | None = Field(default=None, description="Git commit hash")
    config_hash: str | None = Field(
        default=None, description="SHA256 hash of pipeline config"
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


# =============================================================================
# Bronze Layer Components
# =============================================================================


class RateLimitInfo(BaseModel):
    """Rate limit information from API response headers.

    Attributes:
        remaining: Remaining requests in current window (X-RateLimit-Remaining).
        limit: Maximum requests allowed in window (X-RateLimit-Limit).
        reset_at: Timestamp when rate limit resets (X-RateLimit-Reset).
        retry_after_seconds: Seconds to wait before retry (Retry-After header).
    """

    remaining: int | None = Field(
        default=None, description="Remaining requests in current window"
    )
    limit: int | None = Field(
        default=None, description="Maximum requests allowed in window"
    )
    reset_at: datetime | None = Field(
        default=None, description="Timestamp when rate limit resets"
    )
    retry_after_seconds: float | None = Field(
        default=None, description="Seconds to wait before retry"
    )


class APIRequestDetails(BaseModel):
    """Detailed API request information for audit and debugging.

    Captures per-request metadata including endpoint, parameters,
    response size, timing, and rate limit status.

    Attributes:
        endpoint: API endpoint path (e.g., "/chembl/api/data/activity").
        base_url: Base URL of the API (e.g., "https://www.ebi.ac.uk").
        query_params: Query parameters used in request.
        http_method: HTTP method (GET, POST).
        response_size_bytes: Size of response body in bytes.
        request_duration_ms: Request duration in milliseconds.
        status_code: HTTP response status code.
        rate_limit: Rate limit information from response headers.
        timestamp: UTC timestamp when request was made.
    """

    endpoint: str = Field(description="API endpoint path")
    base_url: str = Field(description="Base URL of the API")
    query_params: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict, description="Query parameters"
    )
    http_method: Literal["GET", "POST", "HEAD"] = Field(
        default="GET", description="HTTP method"
    )
    response_size_bytes: int = Field(
        default=0, description="Size of response body in bytes"
    )
    request_duration_ms: float = Field(
        default=0.0, description="Request duration in milliseconds"
    )
    status_code: int = Field(default=200, description="HTTP response status code")
    rate_limit: RateLimitInfo | None = Field(
        default=None, description="Rate limit information"
    )
    timestamp: datetime | None = Field(
        default=None, description="UTC timestamp when request was made"
    )


class SourceMetadata(BaseModel):
    """Data source information for Bronze layer.

    Extended to include detailed API request tracking for audit,
    debugging, and monitoring purposes.

    Attributes:
        type: Source type (api, csv, parquet).
        url: API URL for API sources.
        file_path: File path for file sources.
        query_string: Query string used for data source filtering
            (e.g., 'assay_type=B&standard_type=IC50').
        watermark_before: Previous watermark timestamp.
        watermark_after: New watermark timestamp after ingestion.
        api_version: Provider API version.
        api_requests: List of detailed API request information.
        total_requests: Total number of API requests made.
        total_response_bytes: Total bytes received from all requests.
        avg_request_duration_ms: Average request duration in milliseconds.
    """

    type: Literal["api", "csv", "parquet"] = Field(
        default="api", description="Source type"
    )
    url: str | None = Field(default=None, description="API URL")
    file_path: str | None = Field(default=None, description="Source file path")
    query_string: str | None = Field(
        default=None,
        description="Query string used for data source filtering (e.g., 'assay_type=B')",
    )
    watermark_before: datetime | None = Field(
        default=None, description="Previous watermark"
    )
    watermark_after: datetime | None = Field(
        default=None, description="New watermark after ingestion"
    )
    api_version: str | None = Field(default=None, description="Provider API version")
    api_requests: list[APIRequestDetails] = Field(
        default_factory=list, description="Detailed API request information"
    )
    total_requests: int = Field(default=0, description="Total number of API requests")
    total_response_bytes: int = Field(
        default=0, description="Total bytes received from all requests"
    )
    avg_request_duration_ms: float = Field(
        default=0.0, description="Average request duration in milliseconds"
    )


class FileOutputMetadata(BaseModel):
    """Individual file output information.

    Attributes:
        path: Relative file path.
        size_bytes: File size in bytes.
        record_count: Number of records in file.
        checksum_blake2: BLAKE2 checksum for integrity.
    """

    path: str = Field(description="Relative file path")
    size_bytes: int = Field(description="File size in bytes")
    record_count: int = Field(description="Number of records")
    checksum_blake2: str | None = Field(default=None, description="BLAKE2 checksum")


class OutputMetadata(BaseModel):
    """Bronze output information.

    Attributes:
        files: List of output files.
        total_records: Total records across all files.
        total_bytes: Total bytes across all files.
        format: Output format (jsonl+zstd).
        compression: Compression algorithm.
    """

    files: list[FileOutputMetadata] = Field(
        default_factory=list, description="Output files"
    )
    total_records: int = Field(default=0, description="Total records")
    total_bytes: int = Field(default=0, description="Total bytes")
    format: str = Field(default="jsonl+zstd", description="Output format")
    compression: str = Field(default="zstd", description="Compression algorithm")


# =============================================================================
# Silver Layer Components
# =============================================================================


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

    @property
    def null_rates(self) -> dict[str, float]:
        """Get null rates for all columns."""
        return {col: metrics.null_rate for col, metrics in self.column_metrics.items()}


# =============================================================================
# Gold Layer Components
# =============================================================================


class SchemaColumnMetadata(BaseModel):
    """Schema column definition.

    Attributes:
        name: Column name.
        type: Column data type.
        nullable: Whether column allows nulls.
    """

    name: str = Field(description="Column name")
    type: str = Field(description="Data type")
    nullable: bool = Field(default=True, description="Nullable")


class SchemaMetadata(BaseModel):
    """Schema contract metadata for Gold layer.

    Attributes:
        contract_path: Path to schema contract file.
        version: Schema version.
        validation: Validation mode (strict for Gold).
        columns: Column definitions.
    """

    contract_path: str | None = Field(
        default=None, description="Path to schema contract file"
    )
    version: str = Field(default="1.0", description="Schema version")
    validation: Literal["strict", "lenient"] = Field(
        default="strict", description="Validation mode"
    )
    columns: list[SchemaColumnMetadata] = Field(
        default_factory=list, description="Column definitions"
    )


class SCDMetadata(BaseModel):
    """SCD Type 2 tracking metadata.

    Attributes:
        enabled: Whether SCD2 is enabled.
        effective_date_column: Column for effective date.
        end_date_column: Column for end date.
        current_flag_column: Column for current flag.
        new_versions_created: Number of new versions created.
        records_expired: Number of records expired.
    """

    enabled: bool = Field(default=False, description="SCD2 enabled")
    effective_date_column: str = Field(
        default="_valid_from", description="Effective date column"
    )
    end_date_column: str = Field(default="_valid_to", description="End date column")
    current_flag_column: str = Field(
        default="_is_current", description="Current flag column"
    )
    new_versions_created: int = Field(default=0, description="New versions created")
    records_expired: int = Field(default=0, description="Records expired")


class GoldOutputMetadata(BaseModel):
    """Gold layer output metrics.

    Attributes:
        record_count: Number of records.
        partition_count: Number of partitions.
        total_bytes: Total size in bytes.
        format: Output format (delta or parquet).
    """

    record_count: int = Field(default=0, description="Record count")
    partition_count: int = Field(default=0, description="Partition count")
    total_bytes: int = Field(default=0, description="Total bytes")
    format: Literal["delta", "parquet"] = Field(
        default="delta", description="Output format"
    )


class SilverOutputMetadata(BaseModel):
    """Silver layer output metrics.

    Attributes:
        record_count: Number of records written.
        content_hash: SHA256 hash of content for change detection.
    """

    record_count: int = Field(default=0, description="Record count")
    content_hash: str | None = Field(
        default=None, description="Content hash for change detection"
    )


# =============================================================================
# Complete Layer Metadata Models
# =============================================================================


class BronzeMetadata(BaseModel):
    """Complete metadata for Bronze layer sidecar file.

    Structure follows RULES.md 2.4 lineage requirements.
    Includes governance metadata block for data stewardship.
    """

    version: str = Field(default="1.0", description="Metadata schema version")
    layer: LayerType = Field(default=LayerType.BRONZE, description="Medallion layer")
    runtime: RuntimeMetadata = Field(description="Runtime context")
    pipeline: PipelineMetadata = Field(description="Pipeline identification")
    source: SourceMetadata = Field(
        default_factory=SourceMetadata, description="Source information"
    )
    output: OutputMetadata = Field(
        default_factory=OutputMetadata, description="Output information"
    )
    environment: EnvironmentMetadata = Field(description="Environment information")
    governance: GovernanceMetadata | None = Field(
        default=None, description="Governance metadata for data stewardship"
    )


class SilverMetadata(BaseModel):
    """Complete metadata for Silver layer sidecar file.

    Includes lineage tracking from Bronze, DQ metrics, and governance metadata.
    """

    version: str = Field(default="1.0", description="Metadata schema version")
    layer: LayerType = Field(default=LayerType.SILVER, description="Medallion layer")
    runtime: RuntimeMetadata = Field(description="Runtime context")
    pipeline: PipelineMetadata = Field(description="Pipeline identification")
    lineage: LineageMetadata = Field(
        default_factory=LineageMetadata, description="Lineage information"
    )
    delta: DeltaMetrics = Field(description="Delta Lake metrics")
    dq_summary: DQSummary = Field(
        default_factory=DQSummary, description="Data quality summary"
    )
    output: SilverOutputMetadata = Field(
        default_factory=SilverOutputMetadata, description="Output metrics"
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


class GoldMetadata(BaseModel):
    """Complete metadata for Gold layer sidecar file.

    Includes schema contract, SCD tracking, and governance metadata.
    """

    model_config = ConfigDict(populate_by_name=True)

    version: str = Field(default="1.0", description="Metadata schema version")
    layer: LayerType = Field(default=LayerType.GOLD, description="Medallion layer")
    runtime: RuntimeMetadata = Field(description="Runtime context")
    pipeline: PipelineMetadata = Field(description="Pipeline identification")
    lineage: LineageMetadata = Field(
        default_factory=LineageMetadata, description="Lineage information"
    )
    schema_info: SchemaMetadata = Field(
        default_factory=SchemaMetadata,
        description="Schema contract",
        alias="schema",
    )
    dq_summary: DQSummary = Field(
        default_factory=DQSummary, description="Data quality summary"
    )
    output: GoldOutputMetadata = Field(
        default_factory=GoldOutputMetadata, description="Output metrics"
    )
    scd: SCDMetadata | None = Field(default=None, description="SCD Type 2 metadata")
    environment: EnvironmentMetadata = Field(description="Environment information")
    governance: GovernanceMetadata | None = Field(
        default=None, description="Governance metadata for data stewardship"
    )
