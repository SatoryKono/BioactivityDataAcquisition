"""Core DQ check result value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType

from bioetl.domain.types import DriftLevel, JsonDict
from bioetl.domain.value_objects.dq_report_enums import DQCheckStatus


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
        object.__setattr__(self, "schema", MappingProxyType(dict(self.schema)))


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
    column_stats: dict[str, JsonDict] = field(default_factory=dict)
    status: DQCheckStatus = DQCheckStatus.PASS


@dataclass(frozen=True, slots=True)
class TypeConformanceResult:
    """Type conformance check result."""

    schema_version: str | None
    pandera_passed: bool
    errors: tuple[str, ...] = ()
    type_coercions: dict[str, JsonDict] = field(default_factory=dict)
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

    top_values: tuple[JsonDict, ...]
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


def _as_tuple(value: object) -> tuple[object, ...]:
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    return tuple(value)  # type: ignore[arg-type]


def _freeze_type_change(item: object) -> object:
    from types import MappingProxyType

    if isinstance(item, dict):
        return MappingProxyType(dict(item))
    return item


def _freeze_type_changes(items: tuple[object, ...]) -> tuple[object, ...]:
    return tuple(_freeze_type_change(item) for item in items)


@dataclass(frozen=True, slots=True)
class SchemaDriftResult:
    """Schema drift detection result."""

    drift_level: DriftLevel
    new_fields: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    type_changes: tuple[dict[str, str], ...] = ()
    status: DQCheckStatus = DQCheckStatus.PASS

    def _normalize_field_tuples(self) -> None:
        object.__setattr__(self, "new_fields", _as_tuple(self.new_fields))
        object.__setattr__(self, "missing_fields", _as_tuple(self.missing_fields))
        object.__setattr__(self, "type_changes", _as_tuple(self.type_changes))

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        self._normalize_field_tuples()
        # Deep-freeze each type-change mapping.
        object.__setattr__(
            self,
            "type_changes",
            _freeze_type_changes(self.type_changes),
        )


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


__all__ = [
    "CategoricalDistribution",
    "ContentHashIntegrityResult",
    "DeduplicationStatsResult",
    "DriftLevel",
    "EncodingValidationResult",
    "FileIntegrityResult",
    "NullRateResult",
    "NumericDistribution",
    "RecordCountResult",
    "SchemaDriftResult",
    "SchemaSnapshotResult",
    "TypeConformanceResult",
    "UniquenessResult",
    "ValueDistributionResult",
]
