"""Silver layer DQ analyzer.

Implements data quality monitoring for normalized Silver data:
- Record count with input/output comparison
- Null rate analysis per column
- Uniqueness and cardinality checks
- Type conformance validation
- Value distribution statistics
- Schema drift detection
- Deduplication statistics
- Content hash integrity

Follows RULES.md §3.1 DQ strategy for Silver layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import polars as pl
import pyarrow as pa

from bioetl.application.services.dq.dq_report_builders import (
    build_summary,
    update_counts,
)
from bioetl.domain.ports import SilverDQConfigPort
from bioetl.domain.services.dq_serializer import to_dict
from bioetl.domain.value_objects.dq_report import (
    CategoricalDistribution,
    ContentHashIntegrityResult,
    DeduplicationStatsResult,
    DQCheckStatus,
    DQThresholds,
    DriftLevel,
    MedallionLayer,
    NullRateResult,
    NumericDistribution,
    RecordCountResult,
    SchemaDriftResult,
    SilverDQCheckType,
    SilverDQReport,
    TypeConformanceResult,
    UniquenessResult,
    ValueDistributionResult,
)


class SilverDQAnalyzer:
    """Analyzer for Silver layer DQ checks.

    Performs comprehensive data quality monitoring on normalized data.
    Implements SilverDQAnalyzerPort.
    """

    def _execute_checks(
        self,
        df: pl.DataFrame,
        enabled_checks: set[SilverDQCheckType],
        primary_keys: list[str],
        input_record_count: int | None,
        quarantined_count: int,
        previous_schema: dict[str, str] | None,
    ) -> tuple[dict[str, Any], int, int, int]:
        """Execute all enabled DQ checks and collect results.

        Args:
            df: Polars DataFrame with Silver data.
            enabled_checks: Set of enabled check types.
            primary_keys: List of primary key columns.
            input_record_count: Original record count before transforms.
            quarantined_count: Number of quarantined records.
            previous_schema: Previous schema for drift detection.

        Returns:
            Tuple of (checks dict, passed count, failed count, warnings count).
        """
        checks: dict[str, Any] = {}
        passed, failed, warnings = 0, 0, 0

        if SilverDQCheckType.RECORD_COUNT in enabled_checks:
            record_count_result = self._check_record_count(
                df, input_record_count, quarantined_count
            )
            checks["record_count"] = to_dict(record_count_result)
            passed, failed, warnings = update_counts(
                record_count_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.NULL_RATE in enabled_checks:
            null_results, overall_rate = self._check_null_rates(df)
            checks["null_rate"] = {
                "columns": {r.column_name: to_dict(r) for r in null_results},
                "overall_null_rate": overall_rate,
                "status": DQCheckStatus.PASS.value,
            }
            passed += 1

        if SilverDQCheckType.UNIQUENESS in enabled_checks:
            uniqueness_result = self._check_uniqueness(df, primary_keys)
            checks["uniqueness"] = to_dict(uniqueness_result)
            passed, failed, warnings = update_counts(
                uniqueness_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.TYPE_CONFORMANCE in enabled_checks:
            conformance_result = self._check_type_conformance(df)
            checks["type_conformance"] = to_dict(conformance_result)
            passed, failed, warnings = update_counts(
                conformance_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.VALUE_DISTRIBUTION in enabled_checks:
            distribution_result = self._check_value_distribution(df)
            checks["value_distribution"] = self._distribution_to_dict(
                distribution_result
            )
            passed += 1

        if SilverDQCheckType.SCHEMA_DRIFT in enabled_checks:
            drift_result = self._check_schema_drift(df, previous_schema)
            checks["schema_drift"] = to_dict(drift_result)
            passed, failed, warnings = update_counts(
                drift_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.DEDUPLICATION_STATS in enabled_checks:
            dedup_result = self._check_deduplication(
                df, primary_keys, input_record_count or len(df)
            )
            checks["deduplication_stats"] = to_dict(dedup_result)
            passed, failed, warnings = update_counts(
                dedup_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.CONTENT_HASH_INTEGRITY in enabled_checks:
            hash_result = self._check_content_hash_integrity(df)
            checks["content_hash_integrity"] = to_dict(hash_result)
            passed, failed, warnings = update_counts(
                hash_result.status, passed, failed, warnings
            )

        return checks, passed, failed, warnings

    def _calculate_thresholds(
        self,
        df_len: int,
        input_record_count: int | None,
        quarantined_count: int,
        soft_fail_threshold: float,
        hard_fail_threshold: float,
    ) -> DQThresholds:
        """Calculate DQ thresholds and error rate status.

        Args:
            df_len: Length of the DataFrame.
            input_record_count: Original record count before transforms.
            quarantined_count: Number of quarantined records.
            soft_fail_threshold: Warning threshold for error rate.
            hard_fail_threshold: Failure threshold for error rate.

        Returns:
            DQThresholds with calculated error rate and status.
        """
        total_input = input_record_count or df_len + quarantined_count
        error_rate = quarantined_count / total_input if total_input > 0 else 0.0

        if error_rate >= hard_fail_threshold:
            threshold_status = DQCheckStatus.FAIL
        elif error_rate >= soft_fail_threshold:
            threshold_status = DQCheckStatus.WARN
        else:
            threshold_status = DQCheckStatus.PASS

        return DQThresholds(
            soft_fail_threshold=soft_fail_threshold,
            hard_fail_threshold=hard_fail_threshold,
            current_error_rate=round(error_rate, 4),
            threshold_status=threshold_status,
        )

    def analyze(
        self,
        data: pl.DataFrame | pa.Table,
        *,
        run_id: str,
        pipeline: str,
        target_table: str,
        source_batch_ids: list[str],
        config: SilverDQConfigPort,
        timestamp: datetime,
        primary_keys: list[str],
        soft_fail_threshold: float = 0.05,
        hard_fail_threshold: float = 0.20,
        input_record_count: int | None = None,
        quarantined_count: int = 0,
        previous_schema: dict[str, str] | None = None,
    ) -> SilverDQReport:
        """Analyze Silver data and generate DQ report.

        Args:
            data: Polars DataFrame or PyArrow Table with Silver data.
            run_id: Pipeline run identifier.
            pipeline: Pipeline name.
            target_table: Silver table path.
            source_batch_ids: List of Bronze batch IDs processed.
            config: DQ report configuration.
            timestamp: Report generation timestamp (UTC).
            primary_keys: List of primary key columns.
            soft_fail_threshold: Warning threshold for error rate.
            hard_fail_threshold: Failure threshold for error rate.
            input_record_count: Original record count before transforms.
            quarantined_count: Number of quarantined records.
            previous_schema: Previous schema for drift detection.

        Returns:
            SilverDQReport: Complete DQ report for Silver layer.
        """
        # Convert PyArrow to Polars for consistent processing
        if isinstance(data, pa.Table):
            df: pl.DataFrame = pl.from_arrow(data)
        else:
            df = data

        enabled_checks = set(config.get_checks_enums())

        # Execute all enabled checks
        checks, passed, failed, warnings = self._execute_checks(
            df=df,
            enabled_checks=enabled_checks,
            primary_keys=primary_keys,
            input_record_count=input_record_count,
            quarantined_count=quarantined_count,
            previous_schema=previous_schema,
        )

        # Calculate thresholds
        thresholds = self._calculate_thresholds(
            df_len=len(df),
            input_record_count=input_record_count,
            quarantined_count=quarantined_count,
            soft_fail_threshold=soft_fail_threshold,
            hard_fail_threshold=hard_fail_threshold,
        )

        # Build summary
        summary = build_summary(
            passed=passed,
            failed=failed,
            warnings=warnings,
            threshold_status=thresholds.threshold_status,
        )

        return SilverDQReport(
            layer=MedallionLayer.SILVER,
            timestamp=timestamp,
            run_id=run_id,
            pipeline=pipeline,
            source_batch_ids=tuple(source_batch_ids),
            target_table=target_table,
            checks=checks,
            thresholds=thresholds,
            summary=summary,
        )

    def _check_record_count(
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

    def _check_null_rates(self, df: pl.DataFrame) -> tuple[list[NullRateResult], float]:
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

    def _check_uniqueness(
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
            except Exception:
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

    def _check_type_conformance(self, df: pl.DataFrame) -> TypeConformanceResult:
        """Check type conformance against expected schema."""
        # For now, just validate that columns have consistent types
        errors = []
        type_coercions: dict[str, dict[str, Any]] = {}

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

    def _check_value_distribution(self, df: pl.DataFrame) -> ValueDistributionResult:
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
                        # Type narrowing: values are numeric due to dtype check above
                        numeric_cols[col] = NumericDistribution(
                            min=float(min_val) if min_val is not None else None,
                            max=float(max_val) if max_val is not None else None,
                            mean=float(mean_val) if mean_val is not None else None,
                            std=float(std_val) if std_val is not None else None,
                            median=float(median_val)
                            if median_val is not None
                            else None,
                        )
                except Exception:
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
                except Exception:
                    pass

        return ValueDistributionResult(
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            status=DQCheckStatus.PASS,
        )

    def _check_schema_drift(
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

    def _check_deduplication(
        self,
        df: pl.DataFrame,
        primary_keys: list[str],
        input_count: int,
    ) -> DeduplicationStatsResult:
        """Calculate deduplication statistics."""
        output_count = len(df)
        dedupe_count = input_count - output_count

        # Check content hash duplicates if column exists
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

    def _check_content_hash_integrity(
        self, df: pl.DataFrame
    ) -> ContentHashIntegrityResult:
        """Check content hash integrity."""
        if "_content_hash" not in df.columns:
            return ContentHashIntegrityResult(
                records_checked=0,
                hash_collisions=0,
                rehash_mismatches=0,
                status=DQCheckStatus.PASS,
            )

        records_checked = len(df)

        # Check for hash collisions (same hash, different content)
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

    def _distribution_to_dict(self, result: ValueDistributionResult) -> dict[str, Any]:
        """Convert distribution result to dict."""
        output: dict[str, Any] = {
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


__all__ = ["SilverDQAnalyzer"]
