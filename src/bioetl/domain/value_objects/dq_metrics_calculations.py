"""Computation helpers for batch DQ metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeGuard

if TYPE_CHECKING:
    from bioetl.domain.types import JsonDict
    from bioetl.domain.value_objects.dq_metrics import ColumnStats


def compute_column_stats(
    records: list[JsonDict],
) -> dict[str, ColumnStats]:
    """Compute column statistics from records."""
    if not records:
        return {}

    all_columns = collect_all_columns(records)
    public_columns = [col for col in all_columns if not col.startswith("_")]

    return {
        col_name: compute_single_column_stats(records, col_name)
        for col_name in public_columns
    }


def collect_all_columns(
    records: list[JsonDict],
) -> set[str]:
    """Collect all unique column names from records."""
    all_columns: set[str] = set()
    for record in records:
        all_columns.update(record.keys())
    return all_columns


def compute_single_column_stats(
    records: list[JsonDict],
    col_name: str,
) -> ColumnStats:
    """Compute statistics for a single column."""
    from bioetl.domain.value_objects.dq_metrics import ColumnStats

    values = [record.get(col_name) for record in records]
    non_null_values = filter_non_null(values)

    null_rate = calculate_null_rate(values, len(records))
    unique_count = calculate_unique_count(non_null_values)
    min_val, max_val, mean_val = compute_numeric_stats(non_null_values)

    return ColumnStats(
        null_rate=null_rate,
        unique_count=unique_count,
        min_value=min_val,
        max_value=max_val,
        mean_value=mean_val,
    )


def filter_non_null(
    values: list[object],
) -> list[object]:
    """Filter out None values from a list."""
    return [v for v in values if v is not None]


def calculate_null_rate(
    values: list[object],
    total: int,
) -> float:
    """Calculate the null rate for a list of values."""
    null_count = sum(1 for v in values if v is None)
    return round(null_count / total, 4)


def make_hashable(value: object) -> object:
    """Convert a value to a hashable representation."""
    if isinstance(value, dict):
        return frozenset((k, make_hashable(v)) for k, v in value.items())
    if isinstance(value, list):
        return tuple(make_hashable(item) for item in value)
    return value


def calculate_unique_count(
    values: list[object],
) -> int:
    """Calculate the count of unique values."""
    if not values:
        return 0
    try:
        return len(set(values))
    except TypeError:
        return len({make_hashable(v) for v in values})


def compute_numeric_stats(
    values: list[object],
) -> tuple[float | None, float | None, float | None]:
    """Compute numeric statistics (min, max, mean) for values."""
    numeric_values = extract_numeric_values(values)
    if not numeric_values:
        return None, None, None

    return (
        round(min(numeric_values), 6),
        round(max(numeric_values), 6),
        round(sum(numeric_values) / len(numeric_values), 6),
    )


def is_valid_numeric(v: object) -> TypeGuard[int | float]:
    """Check if value is a valid numeric (not bool, NaN, or Inf)."""
    if not isinstance(v, (int, float)):
        return False
    if isinstance(v, bool):
        return False
    if v != v:
        return False
    return abs(v) != float("inf")


def extract_numeric_values(
    values: list[object],
) -> list[float]:
    """Extract numeric values from a list of mixed values."""
    return [float(v) for v in values if is_valid_numeric(v)]
