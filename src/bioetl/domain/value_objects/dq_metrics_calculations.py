# pyright: reportArgumentType=false
# Boundary object/payload typing residual at this module.
"""Computation helpers for batch DQ metrics."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, TypeGuard

if TYPE_CHECKING:
    from bioetl.domain.types import JsonDict
    from bioetl.domain.value_objects.dq_metrics import ColumnStats


def compute_column_stats(
    records: list[JsonDict],
) -> dict[str, ColumnStats]:
    """Compute column statistics from records.

    Args:
        records: List of record dictionaries to compute statistics over.

    Returns:
        Mapping of public column names (those not starting with '_') to ColumnStats objects.
        Returns empty dict if records is empty.
    """
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
    """Collect all unique column names from records.

    Args:
        records: List of record dictionaries.

    Returns:
        Set of all unique keys found across all records.
    """
    all_columns: set[str] = set()
    for record in records:
        all_columns.update(record.keys())
    return all_columns


def compute_single_column_stats(
    records: list[JsonDict],
    col_name: str,
) -> ColumnStats:
    """Compute statistics for a single column.

    Args:
        records: List of record dictionaries containing the column.
        col_name: Column name to compute statistics for.

    Returns:
        ColumnStats with null rate, unique count, and numeric stats (min, max, mean).
    """
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
    """Filter out None values from a list.

    Args:
        values: List of values that may contain None entries.

    Returns:
        List with all None values removed.
    """
    return [v for v in values if v is not None]


def calculate_null_rate(
    values: list[object],
    total: int,
) -> float:
    """Calculate the null rate for a list of values.

    Args:
        values: List of values to check for None.
        total: Total record count used as the denominator.

    Returns:
        Null rate rounded to 4 decimal places (0.0 to 1.0).
    """
    null_count = sum(1 for v in values if v is None)
    return round(null_count / total, 4)


def make_hashable(value: object) -> object:
    """Convert a value to a hashable representation.

    Args:
        value: Any value, including dicts and lists that are not natively hashable.

    Returns:
        Hashable equivalent: frozenset for dicts, tuple for lists, original for others.
    """
    if isinstance(value, dict):
        return frozenset((k, make_hashable(v)) for k, v in value.items())
    if isinstance(value, list):
        return tuple(make_hashable(item) for item in value)
    return value


def calculate_unique_count(
    values: list[object],
) -> int:
    """Calculate the count of unique values.

    Args:
        values: List of non-null values to count unique entries in.

    Returns:
        Number of distinct values. Returns 0 if values is empty.
    """
    if not values:
        return 0
    try:
        return len(set(values))
    except TypeError:
        return len({make_hashable(v) for v in values})


def compute_numeric_stats(
    values: list[object],
) -> tuple[float | None, float | None, float | None]:
    """Compute numeric statistics (min, max, mean) for values.

    Args:
        values: List of values to compute statistics over (may contain non-numerics).

    Returns:
        Tuple of (min, max, mean) rounded to 6 decimal places. Returns (None, None, None)
        if no valid numeric values are found.
    """
    numeric_values = extract_numeric_values(values)
    if not numeric_values:
        return None, None, None

    return (
        round(min(numeric_values), 6),
        round(max(numeric_values), 6),
        round(sum(numeric_values) / len(numeric_values), 6),
    )


def is_valid_numeric(v: object) -> TypeGuard[int | float]:
    """Check if value is a valid numeric (not bool, NaN, or Inf).

    Args:
        v: Value to check.

    Returns:
        True if v is a finite, non-boolean int or float; False otherwise.
    """
    if not isinstance(v, (int, float)):
        return False
    if isinstance(v, bool):
        return False
    return math.isfinite(float(v))


def extract_numeric_values(
    values: list[object],
) -> list[float]:
    """Extract numeric values from a list of mixed values.

    Args:
        values: List of mixed-type values to filter.

    Returns:
        List of float-converted valid numeric values, excluding booleans, NaN, and Inf.
    """
    return [float(v) for v in values if is_valid_numeric(v)]
