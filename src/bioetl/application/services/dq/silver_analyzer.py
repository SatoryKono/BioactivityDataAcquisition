"""Silver layer DQ analyzer facade.

Orchestrates data quality monitoring for normalized Silver data by
delegating to focused components:
- SilverStatisticsCalculator: check metric computations
- SilverThresholdChecker: error rate thresholds and key constraints

Implements SilverDQAnalyzerPort. Follows RULES.md §3.1 DQ strategy.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, cast

import polars as pl
import pyarrow as pa

from bioetl.application.services.dq.dq_report_builders import (
    build_summary,
    update_counts,
)
from bioetl.application.services.dq.silver_statistics import SilverStatisticsCalculator
from bioetl.application.services.dq.silver_threshold import SilverThresholdChecker
from bioetl.domain.ports import SilverDQConfigPort
from bioetl.domain.services.dq_serializer import to_dict
from bioetl.domain.types import JsonDict
from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    MedallionLayer,
    SilverDQCheckType,
    SilverDQReport,
)


class SilverDQAnalyzer:
    """Facade for Silver layer DQ checks.

    Orchestrates comprehensive data quality monitoring on normalized data
    by delegating to SilverStatisticsCalculator and SilverThresholdChecker.
    Implements SilverDQAnalyzerPort.
    """

    def __init__(
        self,
        statistics: SilverStatisticsCalculator | None = None,
        threshold_checker: SilverThresholdChecker | None = None,
    ) -> None:
        self._statistics = statistics or SilverStatisticsCalculator()
        self._threshold = threshold_checker or SilverThresholdChecker()

    def _execute_checks(
        self,
        df: pl.DataFrame,
        enabled_checks: set[SilverDQCheckType],
        primary_keys: list[str],
        input_record_count: int | None,
        quarantined_count: int,
        previous_schema: dict[str, str] | None,
        key_nullability_rules: (
            list[
                JsonDict  # Any: DQ check values vary by check type
            ]  # Any: DQ rule definitions have heterogeneous values
            | None
        ),  # Any: DQ check values vary by check type
    ) -> tuple[JsonDict, int, int, int]:
        """Execute all enabled DQ checks and collect results."""
        checks: JsonDict = {}  # Any: DQ check values vary by check type
        passed, failed, warnings = 0, 0, 0

        passed, failed, warnings = self._run_standard_checks(
            df,
            enabled_checks,
            primary_keys,
            input_record_count,
            quarantined_count,
            previous_schema,
            checks,
            passed,
            failed,
            warnings,
        )
        passed = self._run_null_rate_check(df, enabled_checks, checks, passed)
        passed = self._run_value_distribution_check(df, enabled_checks, checks, passed)
        passed, failed, warnings = self._run_key_nullability_check(
            df,
            enabled_checks,
            key_nullability_rules,
            checks,
            passed,
            failed,
            warnings,
        )

        return checks, passed, failed, warnings

    def _run_standard_checks(
        self,
        df: pl.DataFrame,
        enabled_checks: set[SilverDQCheckType],
        primary_keys: list[str],
        input_record_count: int | None,
        quarantined_count: int,
        previous_schema: dict[str, str] | None,
        checks: JsonDict,
        passed: int,
        failed: int,
        warnings: int,
    ) -> tuple[int, int, int]:
        """Run standard DQ checks that follow the to_dict/update_counts pattern."""
        stats = self._statistics
        standard_checks: list[
            tuple[SilverDQCheckType, str, Callable[[], Any]]  # Any: check results vary
        ] = [
            (
                SilverDQCheckType.RECORD_COUNT,
                "record_count",
                lambda: stats.check_record_count(
                    df, input_record_count, quarantined_count
                ),
            ),
            (
                SilverDQCheckType.UNIQUENESS,
                "uniqueness",
                lambda: stats.check_uniqueness(df, primary_keys),
            ),
            (
                SilverDQCheckType.TYPE_CONFORMANCE,
                "type_conformance",
                lambda: stats.check_type_conformance(df),
            ),
            (
                SilverDQCheckType.SCHEMA_DRIFT,
                "schema_drift",
                lambda: stats.check_schema_drift(df, previous_schema),
            ),
            (
                SilverDQCheckType.DEDUPLICATION_STATS,
                "deduplication_stats",
                lambda: stats.check_deduplication(
                    df, primary_keys, input_record_count or len(df)
                ),
            ),
            (
                SilverDQCheckType.CONTENT_HASH_INTEGRITY,
                "content_hash_integrity",
                lambda: stats.check_content_hash_integrity(df),
            ),
        ]
        for check_type, key, handler in standard_checks:
            if check_type in enabled_checks:
                result = handler()
                checks[key] = to_dict(result)
                passed, failed, warnings = update_counts(
                    result.status, passed, failed, warnings
                )
        return passed, failed, warnings

    def _run_null_rate_check(
        self,
        df: pl.DataFrame,
        enabled_checks: set[SilverDQCheckType],
        checks: JsonDict,
        passed: int,
    ) -> int:
        """Run null rate check (always PASS, custom dict format)."""
        if SilverDQCheckType.NULL_RATE in enabled_checks:
            null_results, overall_rate = self._statistics.check_null_rates(df)
            checks["null_rate"] = {
                "columns": {r.column_name: to_dict(r) for r in null_results},
                "overall_null_rate": overall_rate,
                "status": DQCheckStatus.PASS.value,
            }
            passed += 1
        return passed

    def _run_value_distribution_check(
        self,
        df: pl.DataFrame,
        enabled_checks: set[SilverDQCheckType],
        checks: JsonDict,
        passed: int,
    ) -> int:
        """Run value distribution check (always PASS, custom serializer)."""
        if SilverDQCheckType.VALUE_DISTRIBUTION in enabled_checks:
            distribution_result = self._statistics.check_value_distribution(df)
            checks["value_distribution"] = self._statistics.distribution_to_dict(
                distribution_result
            )
            passed += 1
        return passed

    def _run_key_nullability_check(
        self,
        df: pl.DataFrame,
        enabled_checks: set[SilverDQCheckType],
        key_nullability_rules: (
            list[
                JsonDict  # Any: DQ check values vary by check type
            ]  # Any: DQ rule definitions have heterogeneous values
            | None
        ),
        checks: JsonDict,
        passed: int,
        failed: int,
        warnings: int,
    ) -> tuple[int, int, int]:
        """Run key nullability check (delegates to threshold checker)."""
        if SilverDQCheckType.KEY_NULLABILITY in enabled_checks:
            key_nullability_result = self._threshold.check_key_nullability(
                df,
                key_nullability_rules or [],
            )
            checks["key_nullability"] = key_nullability_result
            passed, failed, warnings = update_counts(
                DQCheckStatus(key_nullability_result["status"]),
                passed,
                failed,
                warnings,
            )
        return passed, failed, warnings

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
        key_nullability_rules: (
            list[
                JsonDict  # Any: DQ check values vary by check type
            ]  # Any: DQ rule definitions have heterogeneous values
            | None
        ) = None,  # Any: DQ check values vary by check type
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
            key_nullability_rules: Key nullability constraint rules.

        Returns:
            SilverDQReport: Complete DQ report for Silver layer.
        """
        # Convert PyArrow to Polars for consistent processing
        df = (
            cast("pl.DataFrame", pl.from_arrow(data))
            if isinstance(data, pa.Table)
            else data
        )

        enabled_checks = set(config.get_checks_enums())

        # Execute all enabled checks
        checks, passed, failed, warnings = self._execute_checks(
            df=df,
            enabled_checks=enabled_checks,
            primary_keys=primary_keys,
            input_record_count=input_record_count,
            quarantined_count=quarantined_count,
            previous_schema=previous_schema,
            key_nullability_rules=key_nullability_rules,
        )

        # Calculate thresholds
        thresholds = self._threshold.calculate_thresholds(
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


__all__ = ["SilverDQAnalyzer"]
