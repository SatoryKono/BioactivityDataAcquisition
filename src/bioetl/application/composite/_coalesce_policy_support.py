"""Internal helpers for composite coalescing policies."""

from __future__ import annotations

from collections.abc import Callable, Sequence
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
