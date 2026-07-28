"""Timestamp coalescing helpers for composite join policies."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from bioetl.application.composite._coalesce_policy_support import (
    coalesce_and_drop,
    compatible_columns,
)

_TIMESTAMP_FIELD_SUFFIXES = (
    "updated_at",
    "modified_at",
    "last_updated",
    "timestamp",
    "publication_date",
    "created_at",
)


def resolve_timestamp_companion(
    column: str,
    available_columns: set[str],
) -> str | None:
    """Resolve the companion timestamp column for one qualified value column."""
    parts = column.split(".")
    if len(parts) < 3:
        return None
    prefix = ".".join(parts[:-1])
    for suffix in _TIMESTAMP_FIELD_SUFFIXES:
        candidate = f"{prefix}.{suffix}"
        if candidate != column and candidate in available_columns:
            return candidate
    return None


def timestamp_sort_key(value: object) -> tuple[int, float | str]:
    """Normalize mixed timestamp-like values into a deterministic sort key."""
    if isinstance(value, datetime):
        return (3, value.timestamp())
    if isinstance(value, date):
        return (3, float(value.toordinal()))
    if isinstance(value, int | float):
        return (2, float(value))
    if isinstance(value, str):
        return (1, value)
    return (0, "")


def update_fallback_candidate(
    *,
    value: Any,  # Any: Can hold any row value type during comparison
    rank: int,
    fallback_value: Any,  # Any: Can hold any row value type during comparison
    fallback_rank: int | None,
) -> tuple[Any, int | None]:  # Any: Return type matches the polymorphic row value type
    """Keep the highest-priority non-null value as deterministic fallback."""
    if fallback_rank is None or rank < fallback_rank:
        return value, rank
    return fallback_value, fallback_rank


def resolve_row_timestamp_key(
    *,
    row: dict[str, Any],  # Any: Row values can be of any type (str, int, float, etc.)
    column: str,
    timestamp_columns: dict[str, str | None],
) -> tuple[int, float | str] | None:
    """Return the normalized timestamp key for one value column or ``None``."""
    timestamp_column = timestamp_columns.get(column)
    if timestamp_column is None:
        return None
    timestamp_value = row.get(timestamp_column)
    if timestamp_value is None:
        return None
    return timestamp_sort_key(timestamp_value)


def should_replace_latest_candidate(
    *,
    current_timestamp_key: tuple[int, float | str],
    rank: int,
    best_timestamp_key: tuple[int, float | str] | None,
    best_rank: int | None,
) -> bool:
    """Return whether the current value beats the best timestamp candidate."""
    if best_timestamp_key is None or current_timestamp_key > best_timestamp_key:
        return True
    return (
        current_timestamp_key == best_timestamp_key
        and best_rank is not None
        and rank < best_rank
    )


def pick_latest_timestamp_value(
    *,
    row: dict[str, Any],  # Any: Row values can be of any type (str, int, float, etc.)
    compatible_cols: list[str],
    timestamp_columns: dict[str, str | None],
    priority_rank: dict[str, int],
) -> Any:  # Any: Return type matches the polymorphic row value type
    """Pick the newest non-null field value from one row deterministically."""
    fallback_value: Any = None  # Any: Can hold any row value type during comparison
    fallback_rank: int | None = None
    best_value: Any = None  # Any: Can hold any row value type during comparison
    best_rank: int | None = None
    best_timestamp_key: tuple[int, float | str] | None = None

    for column in compatible_cols:
        value = row.get(column)
        if value is None:
            continue
        rank = priority_rank[column]
        fallback_value, fallback_rank = update_fallback_candidate(
            value=value,
            rank=rank,
            fallback_value=fallback_value,
            fallback_rank=fallback_rank,
        )

        current_timestamp_key = resolve_row_timestamp_key(
            row=row,
            column=column,
            timestamp_columns=timestamp_columns,
        )
        if current_timestamp_key is None:
            continue

        if should_replace_latest_candidate(
            current_timestamp_key=current_timestamp_key,
            rank=rank,
            best_timestamp_key=best_timestamp_key,
            best_rank=best_rank,
        ):
            best_value = value
            best_rank = rank
            best_timestamp_key = current_timestamp_key

    return best_value if best_value is not None else fallback_value


def count_timestamp_companions(timestamp_columns: dict[str, str | None]) -> int:
    """Return how many columns have a resolved timestamp companion."""
    return sum(1 for value in timestamp_columns.values() if value is not None)


def build_latest_timestamp_row_fields(
    compatible_cols: list[str],
    timestamp_columns: dict[str, str | None],
) -> list[str]:
    """Build the struct field list needed for latest-timestamp row evaluation."""
    return list(
        dict.fromkeys(
            [
                *compatible_cols,
                *(
                    timestamp_col
                    for timestamp_col in timestamp_columns.values()
                    if timestamp_col is not None
                ),
            ]
        )
    )


def drop_coalesced_columns(
    df: Any,  # Any: DataFrame can be of any type (polars.DataFrame, pandas.DataFrame, etc.)
    compatible_cols: list[str],
) -> (
    Any  # Any: Return type matches the incoming DataFrame implementation.
):
    """Drop redundant compatible columns after coalescing into the target."""
    cols_to_drop = [column for column in compatible_cols[1:] if column in df.columns]
    return df.drop(cols_to_drop) if cols_to_drop else df


def coalesce_by_latest_timestamp(
    df: Any,  # Any: DataFrame can be of any type (polars.DataFrame, pandas.DataFrame, etc.)
    *,
    ordered_cols: list[str],
) -> (
    Any  # Any: Return type matches the incoming DataFrame implementation.
):
    """Coalesce compatible columns using companion timestamps when present."""
    import polars as pl

    compatible_cols = compatible_columns(df, ordered_cols)
    if len(compatible_cols) <= 1:
        return df

    timestamp_columns = {
        column: resolve_timestamp_companion(column, set(df.columns))
        for column in compatible_cols
    }
    if count_timestamp_companions(timestamp_columns) < 2:
        return coalesce_and_drop(df, compatible_cols)

    target_col = compatible_cols[0]
    row_fields = build_latest_timestamp_row_fields(compatible_cols, timestamp_columns)
    priority_rank = {column: index for index, column in enumerate(compatible_cols)}

    result = df.with_columns(
        pl.struct(row_fields)
        .map_elements(
            lambda row: pick_latest_timestamp_value(
                row=row,
                compatible_cols=compatible_cols,
                timestamp_columns=timestamp_columns,
                priority_rank=priority_rank,
            ),
            return_dtype=df.schema[target_col],
        )
        .alias(target_col)
    )
    return drop_coalesced_columns(result, compatible_cols)
