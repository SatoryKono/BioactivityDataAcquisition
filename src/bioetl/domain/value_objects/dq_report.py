"""Data Quality report value objects.

Immutable value objects representing DQ report results for each Medallion layer.
Part of the domain layer - no I/O dependencies.

Implements RULES.md §3.1.2 - DQ thresholds and report generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from bioetl.domain.medallion import Layer as MedallionLayer
from bioetl.domain.types import DriftLevel, JsonDict


class DQReportFormat(StrEnum):
    """Output format for DQ reports."""

    JSON = "json"
    YAML = "yaml"
    HTML = "html"


class DQCheckStatus(StrEnum):
    """Status of individual DQ check."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class DQReportStatus(StrEnum):
    """Overall status of DQ report."""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


# =============================================================================
# Bronze DQ Check Types
# =============================================================================


class BronzeDQCheckType(StrEnum):
    """Types of DQ checks for Bronze layer."""

    RECORD_COUNT = "record_count"
    FILE_INTEGRITY = "file_integrity"
    SCHEMA_SNAPSHOT = "schema_snapshot"
    RAW_FIELD_PRESENCE = "raw_field_presence"
    ENCODING_VALIDATION = "encoding_validation"


# =============================================================================
# Silver DQ Check Types
# =============================================================================


class SilverDQCheckType(StrEnum):
    """Types of DQ checks for Silver layer."""

    RECORD_COUNT = "record_count"
    NULL_RATE = "null_rate"
    UNIQUENESS = "uniqueness"
    TYPE_CONFORMANCE = "type_conformance"
    VALUE_DISTRIBUTION = "value_distribution"
    SCHEMA_DRIFT = "schema_drift"
    DEDUPLICATION_STATS = "deduplication_stats"
    CONTENT_HASH_INTEGRITY = "content_hash_integrity"
    KEY_NULLABILITY = "key_nullability"


# =============================================================================
# Gold DQ Check Types
# =============================================================================


class GoldDQCheckType(StrEnum):
    """Types of DQ checks for Gold layer."""

    RECORD_COUNT = "record_count"
    COMPLETENESS = "completeness"
    BUSINESS_RULES = "business_rules"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    STATISTICAL_PROFILE = "statistical_profile"
    ANOMALY_DETECTION = "anomaly_detection"
    SCD_INTEGRITY = "scd_integrity"


# =============================================================================
# Check Result Value Objects
# =============================================================================


@dataclass(frozen=True, slots=True)
class RecordCountResult:
    """Record count check result."""

    value: int
    status: DQCheckStatus
    delta_from_last_run: int | None = None
    input_records: int | None = None
    output_records: int | None = None
    quarantined_records: int | None = None
    quarantine_rate: float | None = None


@dataclass(frozen=True, slots=True)
class FileIntegrityResult:
    """File integrity check result."""

    checksum_blake2: str
    size_bytes: int
    compression_ratio: float | None = None
    status: DQCheckStatus = DQCheckStatus.PASS


@dataclass(frozen=True, slots=True)
class SchemaSnapshotResult:
    """Schema snapshot result."""

    fields_detected: int
    schema: dict[str, str]
    new_fields_since_last_run: tuple[str, ...] = ()
    missing_fields_since_last_run: tuple[str, ...] = ()
    status: DQCheckStatus = DQCheckStatus.PASS

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        if isinstance(self.new_fields_since_last_run, list):
            object.__setattr__(
                self, "new_fields_since_last_run", tuple(self.new_fields_since_last_run)
            )
        if isinstance(self.missing_fields_since_last_run, list):
            object.__setattr__(
                self,
                "missing_fields_since_last_run",
                tuple(self.missing_fields_since_last_run),
            )


@dataclass(frozen=True, slots=True)
class EncodingValidationResult:
    """Encoding validation result."""

    encoding_errors: int
    invalid_utf8_records: tuple[int, ...] = ()
    status: DQCheckStatus = DQCheckStatus.PASS

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        if isinstance(self.invalid_utf8_records, list):
            object.__setattr__(
                self, "invalid_utf8_records", tuple(self.invalid_utf8_records)
            )


@dataclass(frozen=True, slots=True)
class NullRateResult:
    """Null rate check result for a column."""

    column_name: str
    null_rate: float
    status: DQCheckStatus
    note: str | None = None


@dataclass(frozen=True, slots=True)
class UniquenessResult:
    """Uniqueness check result."""

    primary_key: str
    unique_count: int
    total_count: int
    duplicate_rate: float
    column_stats: dict[
        str, JsonDict  # Any: port contract allows heterogeneous record values
    ] = (  # Any: port contract allows heterogeneous record values
        field(  # Any: DQ check values vary by check type
            default_factory=dict
        )
    )  # Any: DQ report values vary by check type
    status: DQCheckStatus = DQCheckStatus.PASS


@dataclass(frozen=True, slots=True)
class TypeConformanceResult:
    """Type conformance check result."""

    schema_version: str | None
    pandera_passed: bool
    errors: tuple[str, ...] = ()
    type_coercions: dict[
        str, JsonDict  # Any: port contract allows heterogeneous record values
    ] = (  # Any: port contract allows heterogeneous record values
        field(  # Any: DQ check values vary by check type
            default_factory=dict
        )
    )  # Any: DQ report values vary by check type
    status: DQCheckStatus = DQCheckStatus.PASS

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        if isinstance(self.errors, list):
            object.__setattr__(self, "errors", tuple(self.errors))


@dataclass(frozen=True, slots=True)
class NumericDistribution:
    """Statistics for a numeric column."""

    min: float | None
    max: float | None
    mean: float | None
    std: float | None
    median: float | None = None
    p25: float | None = None
    p75: float | None = None
    p95: float | None = None
    outliers_zscore_3: int = 0


@dataclass(frozen=True, slots=True)
class CategoricalDistribution:
    """Statistics for a categorical column."""

    top_values: tuple[JsonDict, ...]  # Any: DQ report values vary by check type
    cardinality: int

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        if isinstance(self.top_values, list):
            object.__setattr__(self, "top_values", tuple(self.top_values))


@dataclass(frozen=True, slots=True)
class ValueDistributionResult:
    """Value distribution check result."""

    numeric_columns: dict[str, NumericDistribution] = field(default_factory=dict)
    categorical_columns: dict[str, CategoricalDistribution] = field(
        default_factory=dict
    )
    status: DQCheckStatus = DQCheckStatus.PASS


@dataclass(frozen=True, slots=True)
class SchemaDriftResult:
    """Schema drift detection result."""

    drift_level: DriftLevel
    new_fields: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    type_changes: tuple[dict[str, str], ...] = ()
    status: DQCheckStatus = DQCheckStatus.PASS

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        if isinstance(self.new_fields, list):
            object.__setattr__(self, "new_fields", tuple(self.new_fields))
        if isinstance(self.missing_fields, list):
            object.__setattr__(self, "missing_fields", tuple(self.missing_fields))
        if isinstance(self.type_changes, list):
            object.__setattr__(self, "type_changes", tuple(self.type_changes))


@dataclass(frozen=True, slots=True)
class DeduplicationStatsResult:
    """Deduplication statistics result."""

    input_before_dedupe: int
    duplicates_by_content_hash: int
    duplicates_by_business_key: int
    output_after_dedupe: int
    status: DQCheckStatus = DQCheckStatus.PASS


@dataclass(frozen=True, slots=True)
class ContentHashIntegrityResult:
    """Content hash integrity check result."""

    records_checked: int
    hash_collisions: int
    rehash_mismatches: int
    status: DQCheckStatus = DQCheckStatus.PASS


@dataclass(frozen=True, slots=True)
class CompletenessResult:
    """Completeness check result for Gold layer."""

    required_fields: dict[str, float]
    overall_completeness_score: float
    minimum_threshold: float
    status: DQCheckStatus


@dataclass(frozen=True, slots=True)
class BusinessRuleResult:
    """Single business rule check result."""

    rule_id: str
    name: str
    description: str
    passed: bool
    violations: int | None  # None indicates unknown (e.g., exception during check)
    config_path: str | None = None
    layer: str | None = None
    field: str | None = None
    severity: str | None = None
    decision: str | None = None


@dataclass(frozen=True, slots=True)
class BusinessRulesResult:
    """Business rules check result."""

    rules_evaluated: int
    rules_passed: int
    rules_failed: int
    rules: tuple[BusinessRuleResult, ...] = ()
    status: DQCheckStatus = DQCheckStatus.PASS

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        if isinstance(self.rules, list):
            object.__setattr__(self, "rules", tuple(self.rules))


@dataclass(frozen=True, slots=True)
class ForeignKeyResult:
    """Foreign key check result."""

    reference: str
    total_references: int
    valid_references: int
    orphan_records: int
    status: DQCheckStatus
    note: str | None = None


@dataclass(frozen=True, slots=True)
class ReferentialIntegrityResult:
    """Referential integrity check result."""

    foreign_keys: dict[str, ForeignKeyResult] = field(default_factory=dict)
    status: DQCheckStatus = DQCheckStatus.PASS


@dataclass(frozen=True, slots=True)
class StatisticalMetric:
    """Single statistical metric for profiling."""

    current: float
    baseline: float
    ratio: float
    threshold_warning: float
    threshold_critical: float
    status: DQCheckStatus


@dataclass(frozen=True, slots=True)
class StatisticalProfileResult:
    """Statistical profile check result."""

    baseline_period_days: int
    metrics: dict[str, StatisticalMetric] = field(default_factory=dict)
    status: DQCheckStatus = DQCheckStatus.PASS


@dataclass(frozen=True, slots=True)
class AnomalyMetric:
    """Single anomaly detection metric."""

    metric: str
    current_value: float
    baseline_value: float | None = None
    zscore: float | None = None
    threshold_warning: float | None = None
    threshold_critical: float | None = None
    status: str = "normal"


@dataclass(frozen=True, slots=True)
class AnomalyDetectionResult:
    """Anomaly detection check result."""

    cold_start_days: int
    current_day: int
    cold_start_mode: bool
    anomalies_detected: tuple[str, ...] = ()
    metrics_monitored: tuple[AnomalyMetric, ...] = ()
    status: DQCheckStatus = DQCheckStatus.PASS

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        if isinstance(self.anomalies_detected, list):
            object.__setattr__(
                self, "anomalies_detected", tuple(self.anomalies_detected)
            )
        if isinstance(self.metrics_monitored, list):
            object.__setattr__(self, "metrics_monitored", tuple(self.metrics_monitored))


@dataclass(frozen=True, slots=True)
class SCDIntegrityResult:
    """SCD (Slowly Changing Dimension) integrity check result."""

    scd_type: int
    total_entities: int
    entities_with_history: int
    avg_versions_per_entity: float
    version_gaps: int
    temporal_conflicts: int
    overlapping_validity_periods: int
    status: DQCheckStatus = DQCheckStatus.PASS


@dataclass(frozen=True, slots=True)
class DataFreshnessResult:
    """Data freshness check result."""

    max_updated_at: datetime | None
    freshness_lag_seconds: float
    freshness_lag_hours: float
    status: DQCheckStatus


# =============================================================================
# Report Summary
# =============================================================================


@dataclass(frozen=True, slots=True)
class DQReportSummary:
    """Summary of DQ report results."""

    total_checks: int
    passed: int
    failed: int
    warnings: int
    overall_status: DQReportStatus


@dataclass(frozen=True, slots=True)
class DQThresholds:
    """DQ threshold configuration used in report."""

    soft_fail_threshold: float
    hard_fail_threshold: float
    current_error_rate: float
    threshold_status: DQCheckStatus


# =============================================================================
# Main Report Value Objects
# =============================================================================


@dataclass(frozen=True, slots=True)
class BronzeDQReport:
    """DQ report for Bronze layer.

    Attributes:
        layer: Always MedallionLayer.BRONZE.
        timestamp: Report generation timestamp (UTC).
        run_id: Pipeline run identifier.
        pipeline: Pipeline name.
        batch_id: Batch identifier.
        source_file: Path to the Bronze file.
        checks: Dictionary of check type to result.
        summary: Report summary.
    """

    layer: MedallionLayer
    timestamp: datetime
    run_id: str
    pipeline: str
    batch_id: str
    source_file: str
    checks: JsonDict  # Any: DQ report values vary by check type
    summary: DQReportSummary

    def __post_init__(self) -> None:
        """Validate layer is BRONZE."""
        if self.layer != MedallionLayer.BRONZE:
            raise ValueError(f"BronzeDQReport layer must be BRONZE, got {self.layer}")


@dataclass(frozen=True, slots=True)
class SilverDQReport:
    """DQ report for Silver layer.

    Attributes:
        layer: Always MedallionLayer.SILVER.
        timestamp: Report generation timestamp (UTC).
        run_id: Pipeline run identifier.
        pipeline: Pipeline name.
        source_batch_ids: List of Bronze batch IDs processed.
        target_table: Silver table path.
        checks: Dictionary of check type to result.
        thresholds: DQ threshold configuration.
        summary: Report summary.
        metadata_path: Path to corresponding _metadata.yaml file (if generated).
    """

    layer: MedallionLayer
    timestamp: datetime
    run_id: str
    pipeline: str
    source_batch_ids: tuple[str, ...]
    target_table: str
    checks: JsonDict  # Any: DQ report values vary by check type
    thresholds: DQThresholds
    summary: DQReportSummary
    # Cross-reference to metadata
    metadata_path: str | None = None

    def __post_init__(self) -> None:
        """Validate layer and convert lists."""
        if self.layer != MedallionLayer.SILVER:
            raise ValueError(f"SilverDQReport layer must be SILVER, got {self.layer}")
        if isinstance(self.source_batch_ids, list):
            object.__setattr__(self, "source_batch_ids", tuple(self.source_batch_ids))


@dataclass(frozen=True, slots=True)
class GoldDQReport:
    """DQ report for Gold layer.

    Attributes:
        layer: Always MedallionLayer.GOLD.
        timestamp: Report generation timestamp (UTC).
        run_id: Pipeline run identifier.
        pipeline: Pipeline name.
        target_table: Gold table path.
        checks: Dictionary of check type to result.
        data_freshness: Data freshness information.
        summary: Report summary.
    """

    layer: MedallionLayer
    timestamp: datetime
    run_id: str
    pipeline: str
    target_table: str
    checks: JsonDict  # Any: DQ report values vary by check type
    data_freshness: DataFreshnessResult | None
    summary: DQReportSummary

    def __post_init__(self) -> None:
        """Validate layer is GOLD."""
        if self.layer != MedallionLayer.GOLD:
            raise ValueError(f"GoldDQReport layer must be GOLD, got {self.layer}")


__all__ = [
    "AnomalyDetectionResult",
    "AnomalyMetric",
    "BronzeDQCheckType",
    "BronzeDQReport",
    "BusinessRuleResult",
    "BusinessRulesResult",
    "CategoricalDistribution",
    "CompletenessResult",
    "ContentHashIntegrityResult",
    # Check Results
    "DQCheckStatus",
    # Enums
    "DQReportFormat",
    "DQReportStatus",
    # Reports
    "DQReportSummary",
    "DQThresholds",
    "DataFreshnessResult",
    "DeduplicationStatsResult",
    "DriftLevel",
    "EncodingValidationResult",
    "FileIntegrityResult",
    "ForeignKeyResult",
    "GoldDQCheckType",
    "GoldDQReport",
    "MedallionLayer",
    "NullRateResult",
    "NumericDistribution",
    "RecordCountResult",
    "ReferentialIntegrityResult",
    "SCDIntegrityResult",
    "SchemaDriftResult",
    "SchemaSnapshotResult",
    "SilverDQCheckType",
    "SilverDQReport",
    "StatisticalMetric",
    "StatisticalProfileResult",
    "TypeConformanceResult",
    "UniquenessResult",
    "ValueDistributionResult",
]
