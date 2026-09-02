"""Uniqueness statistics helpers for Silver DQ reports."""

from __future__ import annotations

import polars as pl

from bioetl.domain.types import JsonDict
from bioetl.domain.value_objects.dq_report import DQCheckStatus, UniquenessResult


def _uniqueness_ratio(cardinality: int, total_count: int) -> float:
    if total_count <= 0:
        return 0.0
    return round(cardinality / total_count, 4)


def _column_cardinality_entry(cardinality: int, total_count: int) -> JsonDict:
    return {
        "cardinality": cardinality,
        "uniqueness_ratio": _uniqueness_ratio(cardinality, total_count),
    }


def _profile_column_cardinality_fallback(
    df: pl.DataFrame,
    cols_to_check: list[str],
    total_count: int,
    profile_errors: tuple[type[BaseException], ...],
) -> JsonDict:
    """Per-column n_unique fallback when vectorized profiling fails."""
    column_stats: JsonDict = {}
    for col in cols_to_check:
        try:
            cardinality = df[col].n_unique()
        except profile_errors:
            continue
        column_stats[col] = _column_cardinality_entry(cardinality, total_count)
    return column_stats


def _profile_column_cardinality(
    df: pl.DataFrame,
    cols_to_check: list[str],
    total_count: int,
    profile_errors: tuple[type[BaseException], ...],
) -> JsonDict:
    """Profile uniqueness cardinality for a bounded column set."""
    if not cols_to_check:
        return {}
    try:
        # Vectorize cardinality check to avoid massive FFI overhead in python loop
        unique_counts = df.select([pl.col(c).n_unique() for c in cols_to_check]).row(
            0, named=True
        )
    except profile_errors:
        return _profile_column_cardinality_fallback(
            df, cols_to_check, total_count, profile_errors
        )
    return {
        col: _column_cardinality_entry(cardinality, total_count)
        for col, cardinality in unique_counts.items()
    }


def check_uniqueness_stats(
    df: pl.DataFrame,
    primary_keys: list[str],
    profile_errors: tuple[type[BaseException], ...],
) -> UniquenessResult:
    """Calculate uniqueness and per-column cardinality statistics.

    Args:
        df: Input Polars DataFrame to compute uniqueness on.
        primary_keys: List of column names forming the entity primary key.
        profile_errors: Exception types to catch during per-column cardinality
            profiling (e.g. Polars errors for unsupported dtypes).

    Returns:
        UniquenessResult with duplicate count, rate, and per-column cardinality.
        Returns WARN status if any primary key columns are missing.
    """
    if not primary_keys:
        return UniquenessResult(
            primary_key="",
            unique_count=len(df),
            total_count=len(df),
            duplicate_rate=0.0,
            status=DQCheckStatus.PASS,
        )

    existing_keys = [k for k in primary_keys if k in df.columns]
    if not existing_keys:
        return UniquenessResult(
            primary_key=",".join(primary_keys),
            unique_count=len(df),
            total_count=len(df),
            duplicate_rate=0.0,
            status=DQCheckStatus.WARN,
            column_stats={"_note": {"message": "Primary key columns not found"}},
        )

    total_count = len(df)
    # ⚡ Bolt: Use df.n_unique(subset=...) instead of df.select().unique().height
    # Performance impact: Avoids materializing a new DataFrame in memory and skips an intermediate .select() projection.
    # Reduces peak memory usage and compute time significantly for large datasets.
    unique_count = df.n_unique(subset=existing_keys)
    duplicate_count = total_count - unique_count
    duplicate_rate = duplicate_count / total_count if total_count > 0 else 0.0
    column_stats = _profile_column_cardinality(
        df,
        list(df.columns[:10]),
        total_count,
        profile_errors,
    )
    status = DQCheckStatus.PASS if duplicate_rate == 0 else DQCheckStatus.WARN
    return UniquenessResult(
        primary_key=",".join(existing_keys),
        unique_count=unique_count,
        total_count=total_count,
        duplicate_rate=round(duplicate_rate, 4),
        column_stats=column_stats,
        status=status,
    )
