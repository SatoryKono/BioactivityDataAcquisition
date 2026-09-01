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

from itertools import islice

import polars as pl

from bioetl.application.services.dq.silver_statistics_helpers import (
    check_content_hash_integrity_stats as _check_content_hash_integrity_stats,
)
from bioetl.application.services.dq.silver_statistics_helpers import (
    check_deduplication_stats as _check_deduplication_stats,
)
from bioetl.application.services.dq.silver_statistics_helpers import (
    check_null_rates_stats as _check_null_rates_stats,
)
from bioetl.application.services.dq.silver_statistics_helpers import (
    check_schema_drift_stats as _check_schema_drift_stats,
)
from bioetl.application.services.dq.silver_statistics_helpers import (
    check_type_conformance_stats as _check_type_conformance_stats,
)
from bioetl.application.services.dq.silver_statistics_helpers import (
    check_uniqueness_stats as _check_uniqueness_stats,
)
from bioetl.application.services.dq.silver_statistics_helpers import (
    profile_categorical_column as _profile_categorical_column,
)
from bioetl.application.services.dq.silver_statistics_helpers import (
    profile_numeric_column as _profile_numeric_column,
)
from bioetl.application.services.dq.silver_statistics_helpers import (
    value_distribution_to_dict as _value_distribution_to_dict,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.value_objects.dq_report import (
    CategoricalDistribution,
    ContentHashIntegrityResult,
    DeduplicationStatsResult,
    DQCheckStatus,
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
        """Check record count statistics.

        Args:
            df: Input Polars DataFrame to count output records from.
            input_count: Optional upstream record count. If None, derived from
                output + quarantined.
            quarantined_count: Number of records quarantined during transformation.

        Returns:
            RecordCountResult with input, output, and quarantined counts and DQ status.
        """
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
        """Calculate null rates per column.

        Args:
            df: Input Polars DataFrame to compute null rates for.

        Returns:
            Tuple of (per-column NullRateResult list, overall null rate as float).
        """
        return _check_null_rates_stats(df)

    def check_uniqueness(
        self, df: pl.DataFrame, primary_keys: list[str]
    ) -> UniquenessResult:
        """Check uniqueness of primary keys.

        Args:
            df: Input Polars DataFrame to check uniqueness on.
            primary_keys: List of column names forming the entity primary key.

        Returns:
            UniquenessResult with duplicate rate and per-column cardinality stats.
        """
        return _check_uniqueness_stats(df, primary_keys, _SILVER_PROFILE_ERRORS)

    def check_type_conformance(self, df: pl.DataFrame) -> TypeConformanceResult:
        """Check type conformance against expected schema.

        Args:
            df: Input Polars DataFrame to check for mixed-type columns.

        Returns:
            TypeConformanceResult indicating whether any mixed-type columns were found.
        """
        return _check_type_conformance_stats(df)

    def check_value_distribution(self, df: pl.DataFrame) -> ValueDistributionResult:
        """Calculate value distributions for columns.

        Args:
            df: Input Polars DataFrame to profile distributions for.

        Returns:
            ValueDistributionResult with numeric and categorical distributions
            for the first 20 columns.
        """
        numeric_cols: dict[str, NumericDistribution] = {}
        categorical_cols: dict[str, CategoricalDistribution] = {}

        for col, dtype in islice(df.schema.items(), 20):
            if dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32, pl.Int16, pl.Int8):
                numeric_dist = _profile_numeric_column(df, col, _SILVER_PROFILE_ERRORS)
                if numeric_dist is not None:
                    numeric_cols[col] = numeric_dist

            elif dtype in (pl.Utf8, pl.Categorical):
                categorical_dist = _profile_categorical_column(
                    df, col, _SILVER_PROFILE_ERRORS
                )
                if categorical_dist is not None:
                    categorical_cols[col] = categorical_dist

        return ValueDistributionResult(
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            status=DQCheckStatus.PASS,
        )

    def check_schema_drift(
        self, df: pl.DataFrame, previous_schema: dict[str, str] | None
    ) -> SchemaDriftResult:
        """Detect schema drift from previous run.

        Args:
            df: Input Polars DataFrame with the current schema.
            previous_schema: Optional mapping of column name to type string from the
                prior run. If None, drift detection is skipped.

        Returns:
            SchemaDriftResult with new fields, missing fields, and type changes
            relative to the previous schema.
        """
        return _check_schema_drift_stats(df, previous_schema)

    def check_deduplication(
        self,
        df: pl.DataFrame,
        primary_keys: list[str],
        input_count: int,
    ) -> DeduplicationStatsResult:
        """Calculate deduplication statistics.

        Args:
            df: Input Polars DataFrame to compute deduplication stats for.
            primary_keys: List of primary key column names (currently unused,
                content hash is used instead when available).
            input_count: Upstream record count used to compute the deduplication rate.

        Returns:
            DeduplicationStatsResult with duplicate and unique record counts.
        """
        del primary_keys
        content_hash_unique_count: int | None = None
        if "_content_hash" in df.columns:
            content_hash_unique_count = df["_content_hash"].n_unique()
        return _check_deduplication_stats(
            len(df), input_count, content_hash_unique_count
        )

    def check_content_hash_integrity(
        self, df: pl.DataFrame
    ) -> ContentHashIntegrityResult:
        """Check content hash integrity.

        Args:
            df: Input Polars DataFrame to check the '_content_hash' column on.

        Returns:
            ContentHashIntegrityResult with hash column presence and uniqueness stats.
        """
        hash_collision_count: int | None = None
        if "_content_hash" in df.columns:
            hash_counts = df["_content_hash"].value_counts()
            duplicates = hash_counts.filter(pl.col("count") > 1)
            hash_collision_count = len(duplicates)
        return _check_content_hash_integrity_stats(len(df), hash_collision_count)

    def distribution_to_dict(
        self, result: ValueDistributionResult
    ) -> JsonDict:  # Any: DQ check values vary by check type
        """Convert distribution result to dict.

        Args:
            result: ValueDistributionResult to serialize to a plain dict.

        Returns:
            Dict with 'numeric_columns' and 'categorical_columns' sub-dicts and
            'status' string, compatible with DQ report serialization.
        """
        return _value_distribution_to_dict(result)


__all__ = ["SilverStatisticsCalculator"]
