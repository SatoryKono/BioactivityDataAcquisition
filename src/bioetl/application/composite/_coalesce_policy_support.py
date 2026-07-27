"""Internal helpers for composite coalescing policies."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date, datetime
from typing import Any, Protocol

from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.application.composite.join_planner_helpers import parse_pipeline_name

_TIMESTAMP_FIELD_SUFFIXES = (
    "updated_at",
    "modified_at",
    "last_updated",
    "timestamp",
    "publication_date",
    "created_at",
)


class _ColumnPriorityProvider(Protocol):
    """Shared priority-ordering surface exposed by ``ColumnOrderService``."""

    def collect_field_columns(
        self,
        field: str,
        enrichers: Sequence[
            Any  # Any: Enrichers implement provider-specific enrichment protocols.
        ],
        available_columns: set[str],
        seed_pipeline: str | None,
    ) -> list[str]: ...

    def order_columns_by_priority(
        self,
        field: str,
        columns: list[str],
        priorities: tuple[str, ...],
        seed_pipeline: str | None,
    ) -> list[str]: ...

    def filter_compatible_columns(
        self,
        df: Any,  # Any: DataFrame can be of any type (polars.DataFrame, pandas.DataFrame, etc.)
        field: str,
        ordered_cols: list[str],
        can_coalesce: Callable[
            [Any, str, str], bool  # Any: DataFrame may be Polars/Pandas-like.
        ],
    ) -> tuple[list[str], list[str]]: ...


def extract_field_from_qualified(column: str) -> str:
    """Extract field name from qualified column (x.y.z -> z)."""
    parts = column.split(".")
    if len(parts) == 3:
        return parts[2]
    return column


def can_coalesce(
    df: Any,  # Any: DataFrame can be of any type (polars.DataFrame, pandas.DataFrame, etc.)
    col1: str,
    col2: str,
) -> bool:
    """Check if two columns can be coalesced without type breakage."""
    import polars as pl

    type1 = df[col1].dtype
    type2 = df[col2].dtype

    if type1 == type2:
        return True
    if type1 == pl.Null or type2 == pl.Null:
        return True
    return isinstance(type1, pl.List) == isinstance(type2, pl.List)


def build_field_groups(
    df: Any,  # Any: DataFrame can be of any type (polars.DataFrame, pandas.DataFrame, etc.)
) -> dict[str, list[str]]:
    """Group non-system columns by field name."""
    field_groups: dict[str, list[str]] = {}
    for col in df.columns:
        if col.startswith("_"):
            continue
        field = extract_field_from_qualified(col)
        field_groups.setdefault(field, []).append(col)
    return field_groups


def sort_columns(
    columns: list[str],
    seed_prefix_value: str | None,
    *,
    prefer_seed: bool,
) -> list[str]:
    """Sort columns with either seed-first or enricher-first strategy."""

    def sort_key(col: str) -> tuple[int, str]:
        is_seed = bool(seed_prefix_value and col.startswith(seed_prefix_value))
        priority = (0 if is_seed else 1) if prefer_seed else 1 if is_seed else 0
        return (priority, col)

    return sorted(columns, key=sort_key)


def compatible_columns(
    df: Any,  # Any: DataFrame can be of any type (polars.DataFrame, pandas.DataFrame, etc.)
    ordered_cols: list[str],
) -> list[str]:
    """Keep the leading column and all columns type-compatible with it."""
    if not ordered_cols:
        return []

    base_col = ordered_cols[0]
    result = [base_col]
    for col in ordered_cols[1:]:
        if can_coalesce(df, base_col, col):
            result.append(col)
    return result


def coalesce_and_drop(
    df: Any,  # Any: DataFrame can be of any type (polars.DataFrame, pandas.DataFrame, etc.)
    compatible_cols: list[str],
) -> (
    Any  # Any: Return type matches the incoming DataFrame implementation.
):
    """Coalesce compatible columns into first and drop the rest."""
    import polars as pl

    if len(compatible_cols) <= 1:
        return df

    target_col = compatible_cols[0]
    result = df.with_columns(
        pl.coalesce(*[pl.col(col) for col in compatible_cols]).alias(target_col)
    )
    cols_to_drop = [col for col in compatible_cols[1:] if col in result.columns]
    if cols_to_drop:
        return result.drop(cols_to_drop)
    return result


def seed_prefix(seed_pipeline: str | None) -> str | None:
    """Build seed provider.entity prefix used for source ordering."""
    if not seed_pipeline:
        return None

    try:
        provider, entity = parse_pipeline_name(seed_pipeline)
        return f"{provider}.{entity}."
    except ValueError:
        return None


def resolve_priority_provider(
    priority_orderer: _ColumnPriorityProvider | None,
    order_service: ColumnOrderService | None,
) -> _ColumnPriorityProvider:
    """Return the preferred column ordering implementation."""
    if order_service is not None:
        return order_service
    assert priority_orderer is not None
    return priority_orderer


def apply_field_priority(
    df: Any,  # Any: DataFrame can be of any type (polars.DataFrame, pandas.DataFrame, etc.)
    *,
    provider: _ColumnPriorityProvider,
    field: str,
    priorities: tuple[str, ...],
    enrichers: Sequence[
        Any  # Any: Enrichers implement provider-specific enrichment protocols.
    ],
    available_columns: set[str],
    seed_pipeline: str | None,
    can_coalesce_fn: Callable[
        [Any, str, str], bool  # Any: DataFrame may be Polars/Pandas-like.
    ],
) -> (
    Any  # Any: Return type matches the incoming DataFrame implementation.
):
    """Apply one explicit field-priority rule and return updated DataFrame."""
    columns = provider.collect_field_columns(
        field,
        enrichers,
        available_columns,
        seed_pipeline,
    )
    if len(columns) <= 1:
        return df

    ordered_cols = provider.order_columns_by_priority(
        field,
        columns,
        priorities,
        seed_pipeline,
    )
    if not ordered_cols:
        return df

    compatible_cols, _incompatible_cols = provider.filter_compatible_columns(
        df,
        field,
        ordered_cols,
        can_coalesce_fn,
    )
    return coalesce_and_drop(df, compatible_cols)


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
