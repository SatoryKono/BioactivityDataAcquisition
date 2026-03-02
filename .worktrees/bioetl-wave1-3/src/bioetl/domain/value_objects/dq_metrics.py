"""Batch Data Quality metrics value object.

Immutable value object containing DQ metrics for a batch of records.
Used to transfer DQ information from validation to metadata writing.

Implements REQ-DQ-001: DQ metrics in Silver metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import ColumnMetrics, DQSummary, SchemaDrift


@dataclass(frozen=True, slots=True)
class ColumnStats:
    """Per-column statistics computed during validation.

    Attributes:
        null_rate: Fraction of null values (0.0-1.0).
        unique_count: Number of unique values.
        min_value: Minimum value (for numeric columns).
        max_value: Maximum value (for numeric columns).
        mean_value: Mean value (for numeric columns).
    """

    null_rate: float = 0.0
    unique_count: int | None = None
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None

    def to_column_metrics(self) -> ColumnMetrics:
        """Convert to ColumnMetrics model for metadata.

        Returns:
            ColumnMetrics instance for Silver metadata.
        """
        from bioetl.domain.models.metadata import ColumnMetrics

        return ColumnMetrics(
            null_rate=self.null_rate,
            unique_count=self.unique_count,
            min=self.min_value,
            max=self.max_value,
            mean=self.mean_value,
        )


@dataclass(frozen=True, slots=True)
class SchemaDriftInfo:
    """Schema drift detection information.

    Attributes:
        status: Drift severity (info, warn, critical).
        new_fields: List of new fields detected.
        missing_fields: List of missing fields detected.
    """

    status: str = "info"  # Literal["info", "warn", "critical"]
    new_fields: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Convert lists to tuples for immutability."""
        if isinstance(self.new_fields, list):
            object.__setattr__(self, "new_fields", tuple(self.new_fields))
        if isinstance(self.missing_fields, list):
            object.__setattr__(self, "missing_fields", tuple(self.missing_fields))

    def to_schema_drift(self) -> SchemaDrift:
        """Convert to SchemaDrift model for metadata.

        Returns:
            SchemaDrift instance for Silver metadata.
        """
        from bioetl.domain.models.metadata import SchemaDrift

        return SchemaDrift(
            status=self.status,  # type: ignore[arg-type]
            new_fields=list(self.new_fields),
            missing_fields=list(self.missing_fields),
        )

    @property
    def has_drift(self) -> bool:
        """Check if any schema drift was detected."""
        return bool(self.new_fields or self.missing_fields)


@dataclass(frozen=True, slots=True)
class BatchDQMetrics:
    """Data Quality metrics for a batch of records.

    Immutable value object containing comprehensive DQ metrics computed
    during batch validation. Used to populate DQSummary in Silver metadata.

    Attributes:
        total_records: Total number of records in the batch.
        valid_records: Number of records that passed validation.
        error_records: Number of records that failed validation (quarantined).
        warning_records: Number of records with warnings.
        column_stats: Per-column statistics.
        schema_drift: Schema drift information if detected.
        validation_errors: List of validation error messages.
    """

    total_records: int = 0
    valid_records: int = 0
    error_records: int = 0
    warning_records: int = 0
    column_stats: dict[str, ColumnStats] = field(default_factory=dict)
    schema_drift: SchemaDriftInfo | None = None
    validation_errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate and ensure immutability."""
        if isinstance(self.validation_errors, list):
            object.__setattr__(self, "validation_errors", tuple(self.validation_errors))
        # Note: column_stats dict values are frozen dataclasses, so immutable

    @property
    def error_rate(self) -> float:
        """Calculate error rate as fraction of total records.

        Returns:
            Error rate between 0.0 and 1.0.
        """
        if self.total_records == 0:
            return 0.0
        return self.error_records / self.total_records

    @property
    def validation_passed(self) -> bool:
        """Check if validation passed (no errors).

        Returns:
            True if error_records is 0.
        """
        return self.error_records == 0

    def to_dq_summary(self) -> DQSummary:
        """Convert to DQSummary model for metadata.

        Creates a DQSummary instance suitable for writing to
        Silver layer _metadata.yaml sidecar file.

        Returns:
            DQSummary instance with all metrics populated.
        """
        from bioetl.domain.models.metadata import DQSummary

        # Convert column stats to ColumnMetrics
        column_metrics = {
            col_name: stats.to_column_metrics()
            for col_name, stats in self.column_stats.items()
        }

        # Convert schema drift if present
        schema_drift = (
            self.schema_drift.to_schema_drift()
            if self.schema_drift and self.schema_drift.has_drift
            else None
        )

        return DQSummary(
            total_records=self.total_records,
            valid_records=self.valid_records,
            error_records=self.error_records,
            warning_records=self.warning_records,
            error_rate=self.error_rate,
            column_metrics=column_metrics,
            schema_drift=schema_drift,
            validation_passed=self.validation_passed,
        )

    @classmethod
    def from_records(
        cls,
        records: list[dict[str, Any]],
        error_count: int = 0,
        warning_count: int = 0,
        validation_errors: list[str] | None = None,
        schema_drift: SchemaDriftInfo | None = None,
    ) -> BatchDQMetrics:
        """Create BatchDQMetrics by computing column stats from records.

        Factory method that calculates column statistics from a list
        of record dictionaries.

        Args:
            records: List of record dictionaries to analyze.
            error_count: Number of records that failed validation.
            warning_count: Number of records with warnings.
            validation_errors: List of validation error messages.
            schema_drift: Schema drift information if detected.

        Returns:
            BatchDQMetrics instance with computed statistics.
        """
        total = len(records)
        if total == 0:
            return cls(
                total_records=0,
                valid_records=0,
                error_records=error_count,
                warning_records=warning_count,
                validation_errors=tuple(validation_errors or []),
                schema_drift=schema_drift,
            )

        # Compute column statistics
        column_stats = _compute_column_stats(records)

        return cls(
            total_records=total,
            valid_records=total - error_count,
            error_records=error_count,
            warning_records=warning_count,
            column_stats=column_stats,
            schema_drift=schema_drift,
            validation_errors=tuple(validation_errors or []),
        )


def _compute_column_stats(records: list[dict[str, Any]]) -> dict[str, ColumnStats]:
    """Compute column statistics from records.

    Args:
        records: List of record dictionaries.

    Returns:
        Dictionary mapping column names to ColumnStats.
    """
    if not records:
        return {}

    all_columns = _collect_all_columns(records)
    public_columns = [col for col in all_columns if not col.startswith("_")]

    return {
        col_name: _compute_single_column_stats(records, col_name)
        for col_name in public_columns
    }


def _collect_all_columns(records: list[dict[str, Any]]) -> set[str]:
    """Collect all unique column names from records.

    Args:
        records: List of record dictionaries.

    Returns:
        Set of column names.
    """
    all_columns: set[str] = set()
    for record in records:
        all_columns.update(record.keys())
    return all_columns


def _compute_single_column_stats(
    records: list[dict[str, Any]], col_name: str
) -> ColumnStats:
    """Compute statistics for a single column.

    Args:
        records: List of record dictionaries.
        col_name: Name of the column to analyze.

    Returns:
        ColumnStats for the column.
    """
    values = [record.get(col_name) for record in records]
    non_null_values = _filter_non_null(values)

    null_rate = _calculate_null_rate(values, len(records))
    unique_count = _calculate_unique_count(non_null_values)
    min_val, max_val, mean_val = _compute_numeric_stats(non_null_values)

    return ColumnStats(
        null_rate=null_rate,
        unique_count=unique_count,
        min_value=min_val,
        max_value=max_val,
        mean_value=mean_val,
    )


def _filter_non_null(values: list[Any]) -> list[Any]:
    """Filter out None values from a list.

    Args:
        values: List of values.

    Returns:
        List of non-None values.
    """
    return [v for v in values if v is not None]


def _calculate_null_rate(values: list[Any], total: int) -> float:
    """Calculate the null rate for a list of values.

    Args:
        values: List of values.
        total: Total number of records.

    Returns:
        Null rate rounded to 4 decimal places.
    """
    null_count = sum(1 for v in values if v is None)
    return round(null_count / total, 4)


def _make_hashable(value: Any) -> Any:  # Any: record vals vary
    """Convert a value to a hashable representation.

    Args:
        value: Value to convert.

    Returns:
        Hashable representation of the value.
    """
    if isinstance(value, dict):
        # Convert dict to a frozenset of key-value tuples (recursively)
        return frozenset((k, _make_hashable(v)) for k, v in value.items())
    if isinstance(value, list):
        # Convert list to tuple (recursively)
        return tuple(_make_hashable(item) for item in value)
    return value


def _calculate_unique_count(values: list[Any]) -> int:
    """Calculate the count of unique values.

    Args:
        values: List of non-null values.

    Returns:
        Number of unique values, or 0 if empty.
    """
    if not values:
        return 0
    try:
        return len(set(values))
    except TypeError:
        # Handle unhashable types (lists, dicts) by converting to hashable
        return len({_make_hashable(v) for v in values})


def _compute_numeric_stats(
    values: list[Any],
) -> tuple[float | None, float | None, float | None]:
    """Compute numeric statistics (min, max, mean) for values.

    Args:
        values: List of values (may contain non-numeric).

    Returns:
        Tuple of (min, max, mean), all None if no numeric values.
    """
    numeric_values = _extract_numeric_values(values)
    if not numeric_values:
        return None, None, None

    return (
        round(min(numeric_values), 6),
        round(max(numeric_values), 6),
        round(sum(numeric_values) / len(numeric_values), 6),
    )


def _is_valid_numeric(v: Any) -> bool:  # Any: heterogeneous record values
    """Check if value is a valid numeric (not bool, NaN, or Inf).

    Args:
        v: Value to check.

    Returns:
        True if value is a valid finite number.
    """
    if not isinstance(v, (int, float)):
        return False
    if isinstance(v, bool):
        return False
    if v != v:  # NaN check: NaN != NaN
        return False
    return abs(v) != float("inf")


def _extract_numeric_values(values: list[Any]) -> list[float]:
    """Extract numeric values from a list of mixed values.

    Args:
        values: List of values (may contain non-numeric).

    Returns:
        List of float values.
    """
    return [float(v) for v in values if _is_valid_numeric(v)]


__all__ = [
    "BatchDQMetrics",
    "ColumnStats",
    "SchemaDriftInfo",
]
