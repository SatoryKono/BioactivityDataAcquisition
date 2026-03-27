"""Pure helpers for composite coalesce policy orchestration."""

from __future__ import annotations

__all__ = [
    "build_field_groups",
    "can_coalesce",
    "coalesce_and_drop",
    "compatible_columns",
    "extract_field_from_qualified",
    "seed_prefix",
    "sort_columns",
]

from typing import TYPE_CHECKING

from bioetl.application.composite.column_priority_orderer import (
    ColumnPriorityOrderer,
)

if TYPE_CHECKING:
    import polars as pl


def extract_field_from_qualified(column: str) -> str:
    """Extract field name from qualified column (x.y.z -> z)."""
    parts = column.split(".")
    if len(parts) == 3:
        return parts[2]
    return column


def can_coalesce(df: pl.DataFrame, col1: str, col2: str) -> bool:
    """Check if two columns can be coalesced without type breakage."""
    import polars as pl

    type1 = df[col1].dtype
    type2 = df[col2].dtype

    if type1 == type2:
        return True
    if type1 == pl.Null or type2 == pl.Null:
        return True
    return isinstance(type1, pl.List) == isinstance(type2, pl.List)


def build_field_groups(df: pl.DataFrame) -> dict[str, list[str]]:
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

    def sort_key(col: str) -> int:
        is_seed = bool(seed_prefix_value and col.startswith(seed_prefix_value))
        if prefer_seed:
            return 0 if is_seed else 1
        return 1 if is_seed else 0

    return sorted(columns, key=sort_key)


def compatible_columns(df: pl.DataFrame, ordered_cols: list[str]) -> list[str]:
    """Keep the leading column and all columns type-compatible with it."""
    if not ordered_cols:
        return []

    base_col = ordered_cols[0]
    result = [base_col]
    for col in ordered_cols[1:]:
        if can_coalesce(df, base_col, col):
            result.append(col)
    return result


def coalesce_and_drop(df: pl.DataFrame, compatible_cols: list[str]) -> pl.DataFrame:
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
        provider, entity = ColumnPriorityOrderer._parse_pipeline_name(seed_pipeline)
        return f"{provider}.{entity}."
    except ValueError:
        return None
