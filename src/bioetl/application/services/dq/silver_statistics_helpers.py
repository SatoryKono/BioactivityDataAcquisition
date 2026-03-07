"""Helper functions for Silver statistics calculator."""

from __future__ import annotations

from typing import cast

import polars as pl

from bioetl.domain.services.dq_serializer import to_dict
from bioetl.domain.types import JsonDict
from bioetl.domain.value_objects.dq_report import (
    CategoricalDistribution,
    ContentHashIntegrityResult,
    DeduplicationStatsResult,
    DQCheckStatus,
    DriftLevel,
    NullRateResult,
    NumericDistribution,
    SchemaDriftResult,
    TypeConformanceResult,
    UniquenessResult,
    ValueDistributionResult,
)


def detect_type_changes(
    current: dict[str, str], previous: dict[str, str]
) -> list[dict[str, str]]:
    """Find fields whose types differ between current and previous schema."""
    return [
        {"field": f, "from": previous[f], "to": current[f]}
        for f in current
        if f in previous and current[f] != previous[f]
    ]


def check_null_rates_stats(df: pl.DataFrame) -> tuple[list[NullRateResult], float]:
    """Calculate per-column and overall null rates."""
    results: list[NullRateResult] = []
    total_nulls = 0
    total_cells = 0
    row_count = len(df)

    for col in df.columns:
        null_count = df[col].null_count()
        null_rate = null_count / row_count if row_count > 0 else 0.0
        total_nulls += null_count
        total_cells += row_count
        status = DQCheckStatus.WARN if null_rate > 0.5 else DQCheckStatus.PASS
        results.append(
            NullRateResult(
                column_name=col,
                null_rate=round(null_rate, 4),
                status=status,
            )
        )

    overall_null_rate = total_nulls / total_cells if total_cells > 0 else 0.0
    return results, round(overall_null_rate, 4)


def check_uniqueness_stats(
    df: pl.DataFrame,
    primary_keys: list[str],
    profile_errors: tuple[type[BaseException], ...],
) -> UniquenessResult:
    """Calculate uniqueness and per-column cardinality statistics."""
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
    unique_count = df.select(existing_keys).unique().height
    duplicate_count = total_count - unique_count
    duplicate_rate = duplicate_count / total_count if total_count > 0 else 0.0

    column_stats: JsonDict = {}
    for col in df.columns[:10]:
        try:
            cardinality = df[col].n_unique()
            column_stats[col] = {
                "cardinality": cardinality,
                "uniqueness_ratio": (
                    round(cardinality / total_count, 4) if total_count > 0 else 0.0
                ),
            }
        except profile_errors:
            # Some Polars dtypes can fail n_unique() for profiling purposes.
            continue

    status = DQCheckStatus.PASS if duplicate_rate == 0 else DQCheckStatus.WARN
    return UniquenessResult(
        primary_key=",".join(existing_keys),
        unique_count=unique_count,
        total_count=total_count,
        duplicate_rate=round(duplicate_rate, 4),
        column_stats=column_stats,
        status=status,
    )


def check_type_conformance_stats(df: pl.DataFrame) -> TypeConformanceResult:
    """Check for mixed/object columns and build conformance result."""
    errors = []
    type_coercions: dict[str, JsonDict] = {}

    for col in df.columns:
        if df[col].dtype == pl.Object:
            errors.append(f"Column {col} has mixed types (Object)")

    status = DQCheckStatus.PASS if not errors else DQCheckStatus.WARN
    return TypeConformanceResult(
        schema_version=None,
        pandera_passed=len(errors) == 0,
        errors=tuple(errors),
        type_coercions=type_coercions,
        status=status,
    )


def check_schema_drift_stats(
    df: pl.DataFrame, previous_schema: dict[str, str] | None
) -> SchemaDriftResult:
    """Detect schema drift compared with previous schema snapshot."""
    current_schema = {col: str(df[col].dtype) for col in df.columns}

    if previous_schema is None:
        return SchemaDriftResult(
            drift_level=DriftLevel.INFO,
            status=DQCheckStatus.PASS,
        )

    new_fields = [f for f in current_schema if f not in previous_schema]
    missing_fields = [f for f in previous_schema if f not in current_schema]
    type_changes = detect_type_changes(current_schema, previous_schema)
    is_critical = bool(missing_fields or type_changes)
    return SchemaDriftResult(
        drift_level=DriftLevel.CRITICAL if is_critical else DriftLevel.INFO,
        new_fields=tuple(new_fields),
        missing_fields=tuple(missing_fields),
        type_changes=tuple(type_changes),
        status=DQCheckStatus.WARN if is_critical else DQCheckStatus.PASS,
    )


def check_deduplication_stats(
    df_len: int,
    input_count: int,
    content_hash_unique_count: int | None,
) -> DeduplicationStatsResult:
    """Calculate deduplication statistics from input/output counts."""
    output_count = df_len
    dedupe_count = input_count - output_count

    content_hash_dupes = 0
    if content_hash_unique_count is not None:
        content_hash_dupes = output_count - content_hash_unique_count

    return DeduplicationStatsResult(
        input_before_dedupe=input_count,
        duplicates_by_content_hash=content_hash_dupes,
        duplicates_by_business_key=dedupe_count - content_hash_dupes,
        output_after_dedupe=output_count,
        status=DQCheckStatus.PASS,
    )


def check_content_hash_integrity_stats(
    df_len: int,
    hash_collision_count: int | None,
) -> ContentHashIntegrityResult:
    """Calculate content-hash collision metrics."""
    if hash_collision_count is None:
        return ContentHashIntegrityResult(
            records_checked=0,
            hash_collisions=0,
            rehash_mismatches=0,
            status=DQCheckStatus.PASS,
        )

    status = DQCheckStatus.PASS if hash_collision_count == 0 else DQCheckStatus.WARN
    return ContentHashIntegrityResult(
        records_checked=df_len,
        hash_collisions=hash_collision_count,
        rehash_mismatches=0,
        status=status,
    )


def value_distribution_to_dict(
    result: ValueDistributionResult,
) -> JsonDict:  # Any: DQ check values vary by check type
    """Convert value-distribution result to serializable dictionary."""
    output: JsonDict = {  # Any: DQ check values vary by check type
        "numeric_columns": {},
        "categorical_columns": {},
        "status": result.status.value,
    }

    for col, numeric_dist in result.numeric_columns.items():
        output["numeric_columns"][col] = to_dict(numeric_dist)

    for col, categorical_dist in result.categorical_columns.items():
        output["categorical_columns"][col] = {
            "top_values": list(categorical_dist.top_values),
            "cardinality": categorical_dist.cardinality,
        }

    return output


def profile_numeric_column(
    df: pl.DataFrame,
    col: str,
    profile_errors: tuple[type[BaseException], ...],
) -> NumericDistribution | None:
    """Build numeric distribution for one column."""
    try:
        stats = df[col].drop_nulls()
        if len(stats) == 0:
            return None
        min_num = cast("int | float | None", stats.min())
        max_num = cast("int | float | None", stats.max())
        mean_num = cast("int | float | None", stats.mean())
        std_num = cast("int | float | None", stats.std())
        median_num = cast("int | float | None", stats.median())
        return NumericDistribution(
            min=float(min_num) if min_num is not None else None,
            max=float(max_num) if max_num is not None else None,
            mean=float(mean_num) if mean_num is not None else None,
            std=float(std_num) if std_num is not None else None,
            median=float(median_num) if median_num is not None else None,
        )
    except profile_errors:
        return None


def profile_categorical_column(
    df: pl.DataFrame,
    col: str,
    profile_errors: tuple[type[BaseException], ...],
) -> CategoricalDistribution | None:
    """Build categorical distribution for one column."""
    try:
        value_counts = df[col].value_counts().head(5)
        cardinality = df[col].n_unique()
        top_values = []
        for row in value_counts.iter_rows(named=True):
            val = row.get(col) or row.get("value")
            count = row.get("count") or row.get("counts", 0)
            top_values.append(
                {
                    "value": str(val) if val is not None else None,
                    "count": count,
                    "pct": round(count / len(df), 4) if len(df) > 0 else 0,
                }
            )
        return CategoricalDistribution(
            top_values=tuple(top_values),
            cardinality=cardinality,
        )
    except profile_errors:
        return None
