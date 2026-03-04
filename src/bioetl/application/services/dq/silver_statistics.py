"""Silver layer DQ statistics calculator.

Stateless calculator for data quality check metrics:
- Record count with input/output comparison
- Null rate analysis per column
- Uniqueness and cardinality checks
- Type conformance validation
- Value distribution statistics
- Schema drift detection
- Deduplication statistics
- Content hash integrity

Extracted from SilverDQAnalyzer (RF-010).
"""

from __future__ import annotations

from typing import Any, cast

import polars as pl

from bioetl.domain.services.dq_serializer import to_dict
from bioetl.domain.value_objects.dq_report import (
    CategoricalDistribution,
    ContentHashIntegrityResult,
    DeduplicationStatsResult,
    DQCheckStatus,
    DriftLevel,
    NullRateResult,
    NumericDistribution,
    RecordCountResult,
    SchemaDriftResult,
    TypeConformanceResult,
    UniquenessResult,
    ValueDistributionResult,
)

_SILVER_PROFILE_ERRORS = (
    pl.exceptions.PolarsError,
    ValueError,
    TypeError,
    RuntimeError,
)


def _check_deduplication_stats(
    df: pl.DataFrame,
    input_count: int,
) -> DeduplicationStatsResult:
    """Calculate deduplication statistics from input/output counts."""
    output_count = len(df)
    dedupe_count = input_count - output_count

    content_hash_dupes = 0
    if "_content_hash" in df.columns:
        unique_hashes = df["_content_hash"].n_unique()
        content_hash_dupes = output_count - unique_hashes

    return DeduplicationStatsResult(
        input_before_dedupe=input_count,
        duplicates_by_content_hash=content_hash_dupes,
        duplicates_by_business_key=dedupe_count - content_hash_dupes,
        output_after_dedupe=output_count,
        status=DQCheckStatus.PASS,
    )


def _check_content_hash_integrity_stats(df: pl.DataFrame) -> ContentHashIntegrityResult:
    """Calculate content-hash collision metrics."""
    if "_content_hash" not in df.columns:
        return ContentHashIntegrityResult(
            records_checked=0,
            hash_collisions=0,
            rehash_mismatches=0,
            status=DQCheckStatus.PASS,
        )

    records_checked = len(df)
    hash_counts = df["_content_hash"].value_counts()
    duplicates = hash_counts.filter(pl.col("count") > 1)
    hash_collisions = len(duplicates)
    status = DQCheckStatus.PASS if hash_collisions == 0 else DQCheckStatus.WARN

    return ContentHashIntegrityResult(
        records_checked=records_checked,
        hash_collisions=hash_collisions,
        rehash_mismatches=0,  # Would need to recalculate hashes to check
        status=status,
    )


def _value_distribution_to_dict(
    result: ValueDistributionResult,
) -> dict[str, Any]:  # Any: DQ check values vary by check type
    """Convert value-distribution result to serializable dictionary."""
    output: dict[str, Any] = {  # Any: DQ check values vary by check type
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


class SilverStatisticsCalculator:
    """Stateless calculator for Silver layer DQ check metrics.

    Each method computes a specific DQ check result from a Polars DataFrame.
    """

    def check_record_count(
        self,
        df: pl.DataFrame,
        input_count: int | None,
        quarantined_count: int,
    ) -> RecordCountResult:
        """Check record count statistics."""
        output_count = len(df)
        input_records = input_count or (output_count + quarantined_count)
        quarantine_rate = (
            quarantined_count / input_records if input_records > 0 else 0.0
        )

        # Warn if significant data loss
        status = DQCheckStatus.PASS
        if quarantine_rate > 0.1:  # >10% quarantined
            status = DQCheckStatus.WARN

        return RecordCountResult(
            value=output_count,
            status=status,
            input_records=input_records,
            output_records=output_count,
            quarantined_records=quarantined_count,
            quarantine_rate=round(quarantine_rate, 4),
        )

    def check_null_rates(self, df: pl.DataFrame) -> tuple[list[NullRateResult], float]:
        """Calculate null rates per column."""
        results = []
        total_nulls = 0
        total_cells = 0

        for col in df.columns:
            null_count = df[col].null_count()
            total = len(df)
            null_rate = null_count / total if total > 0 else 0.0

            total_nulls += null_count
            total_cells += total

            # Status based on null rate
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

    def check_uniqueness(
        self, df: pl.DataFrame, primary_keys: list[str]
    ) -> UniquenessResult:
        """Check uniqueness of primary keys."""
        if not primary_keys:
            return UniquenessResult(
                primary_key="",
                unique_count=len(df),
                total_count=len(df),
                duplicate_rate=0.0,
                status=DQCheckStatus.PASS,
            )

        # Check which primary keys exist in dataframe
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

        pk_name = ",".join(existing_keys)
        unique_count = df.select(existing_keys).unique().height
        total_count = len(df)
        duplicate_count = total_count - unique_count
        duplicate_rate = duplicate_count / total_count if total_count > 0 else 0.0

        # Calculate column cardinality
        column_stats = {}
        for col in df.columns[:10]:  # Limit to first 10 columns
            try:
                cardinality = df[col].n_unique()
                column_stats[col] = {
                    "cardinality": cardinality,
                    "uniqueness_ratio": round(cardinality / len(df), 4)
                    if len(df) > 0
                    else 0.0,
                }
            except _SILVER_PROFILE_ERRORS:
                # Catch all: cardinality calculation may fail for unhashable types
                # or invalid column access. Skip column from cardinality metrics.
                pass

        status = DQCheckStatus.PASS if duplicate_rate == 0 else DQCheckStatus.WARN

        return UniquenessResult(
            primary_key=pk_name,
            unique_count=unique_count,
            total_count=total_count,
            duplicate_rate=round(duplicate_rate, 4),
            column_stats=column_stats,
            status=status,
        )

    def check_type_conformance(self, df: pl.DataFrame) -> TypeConformanceResult:
        """Check type conformance against expected schema."""
        errors = []
        type_coercions: dict[
            str, dict[str, Any]  # Any: DQ check values vary by check type
        ] = {}  # Any: DQ check values vary by check type

        for col in df.columns:
            dtype = df[col].dtype
            # Check for object/mixed types that indicate inconsistency
            if dtype == pl.Object:
                errors.append(f"Column {col} has mixed types (Object)")

        status = DQCheckStatus.PASS if not errors else DQCheckStatus.WARN

        return TypeConformanceResult(
            schema_version=None,
            pandera_passed=len(errors) == 0,
            errors=tuple(errors),
            type_coercions=type_coercions,
            status=status,
        )

    def check_value_distribution(self, df: pl.DataFrame) -> ValueDistributionResult:
        """Calculate value distributions for columns."""
        numeric_cols: dict[str, NumericDistribution] = {}
        categorical_cols: dict[str, CategoricalDistribution] = {}

        for col in df.columns[:20]:  # Limit to first 20 columns
            dtype = df[col].dtype

            if dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32, pl.Int16, pl.Int8):
                try:
                    stats = df[col].drop_nulls()
                    if len(stats) > 0:
                        min_val = stats.min()
                        max_val = stats.max()
                        mean_val = stats.mean()
                        std_val = stats.std()
                        median_val = stats.median()
                        min_num = cast("int | float | None", min_val)
                        max_num = cast("int | float | None", max_val)
                        mean_num = cast("int | float | None", mean_val)
                        std_num = cast("int | float | None", std_val)
                        median_num = cast("int | float | None", median_val)
                        numeric_cols[col] = NumericDistribution(
                            min=float(min_num) if min_num is not None else None,
                            max=float(max_num) if max_num is not None else None,
                            mean=float(mean_num) if mean_num is not None else None,
                            std=float(std_num) if std_num is not None else None,
                            median=float(median_num)
                            if median_num is not None
                            else None,
                        )
                except _SILVER_PROFILE_ERRORS:
                    # Catch all: numeric stats may fail for mixed types, NaN/Inf,
                    # or non-numeric data in numeric column. Skip column profiling.
                    pass

            elif dtype in (pl.Utf8, pl.Categorical):
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
                    categorical_cols[col] = CategoricalDistribution(
                        top_values=tuple(top_values),
                        cardinality=cardinality,
                    )
                except _SILVER_PROFILE_ERRORS:
                    # Catch all: value_counts() may fail for unhashable types or
                    # large cardinality. Skip column from categorical profiling.
                    pass

        return ValueDistributionResult(
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            status=DQCheckStatus.PASS,
        )

    def check_schema_drift(
        self, df: pl.DataFrame, previous_schema: dict[str, str] | None
    ) -> SchemaDriftResult:
        """Detect schema drift from previous run."""
        current_schema = {col: str(df[col].dtype) for col in df.columns}

        if previous_schema is None:
            return SchemaDriftResult(
                drift_level=DriftLevel.INFO,
                status=DQCheckStatus.PASS,
            )

        new_fields = [f for f in current_schema if f not in previous_schema]
        missing_fields = [f for f in previous_schema if f not in current_schema]
        type_changes = []

        for field in current_schema:
            if (
                field in previous_schema
                and current_schema[field] != previous_schema[field]
            ):
                type_changes.append(
                    {
                        "field": field,
                        "from": previous_schema[field],
                        "to": current_schema[field],
                    }
                )

        # Determine drift level
        if missing_fields or type_changes:
            drift_level = DriftLevel.CRITICAL
            status = DQCheckStatus.WARN
        elif new_fields:
            drift_level = DriftLevel.INFO
            status = DQCheckStatus.PASS
        else:
            drift_level = DriftLevel.INFO
            status = DQCheckStatus.PASS

        return SchemaDriftResult(
            drift_level=drift_level,
            new_fields=tuple(new_fields),
            missing_fields=tuple(missing_fields),
            type_changes=tuple(type_changes),
            status=status,
        )

    def check_deduplication(
        self,
        df: pl.DataFrame,
        primary_keys: list[str],
        input_count: int,
    ) -> DeduplicationStatsResult:
        """Calculate deduplication statistics."""
        del primary_keys
        return _check_deduplication_stats(df, input_count)

    def check_content_hash_integrity(
        self, df: pl.DataFrame
    ) -> ContentHashIntegrityResult:
        """Check content hash integrity."""
        return _check_content_hash_integrity_stats(df)

    def distribution_to_dict(
        self, result: ValueDistributionResult
    ) -> dict[str, Any]:  # Any: DQ check values vary by check type
        """Convert distribution result to dict."""
        return _value_distribution_to_dict(result)


__all__ = ["SilverStatisticsCalculator"]
