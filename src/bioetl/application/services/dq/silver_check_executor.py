"""Execution service for Silver DQ checks.

Extracted from SilverDQAnalyzer to keep facade focused on orchestration.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import polars as pl

from bioetl.application.services.dq.dq_report_builders import update_counts
from bioetl.application.services.dq.silver_statistics import SilverStatisticsCalculator
from bioetl.application.services.dq.silver_threshold import SilverThresholdChecker
from bioetl.domain.behavior.dq_serializer import to_dict
from bioetl.domain.types import JsonDict
from bioetl.domain.value_objects.dq_report import DQCheckStatus, SilverDQCheckType


class SilverCheckExecutor:
    """Execute enabled Silver DQ checks and accumulate statuses."""

    def __init__(
        self,
        statistics: SilverStatisticsCalculator,
        threshold_checker: SilverThresholdChecker,
    ) -> None:
        self._statistics = statistics
        self._threshold = threshold_checker

    def execute_checks(
        self,
        *,
        df: pl.DataFrame,
        enabled_checks: set[SilverDQCheckType],
        primary_keys: list[str],
        input_record_count: int | None,
        quarantined_count: int,
        previous_schema: dict[str, str] | None,
        key_nullability_rules: list[JsonDict] | None,
    ) -> tuple[JsonDict, int, int, int]:
        """Execute all enabled checks and return checks + status counters.

        Args:
            df: Input Polars DataFrame to run DQ checks on.
            enabled_checks: Set of SilverDQCheckType values controlling which
                checks are executed.
            primary_keys: List of column names forming the entity primary key.
            input_record_count: Optional upstream Bronze record count for
                error rate calculation.
            quarantined_count: Number of records quarantined during transformation.
            previous_schema: Optional prior-run schema snapshot for drift detection.
            key_nullability_rules: Optional list of nullability rule dicts for
                business-key null rate checks.

        Returns:
            Tuple of (checks dict, passed count, failed count, warnings count).
            The checks dict maps check name strings to serialized check result dicts.
        """
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
        """Run DQ checks that share to_dict/update_counts flow."""
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
        key_nullability_rules: list[JsonDict] | None,
        checks: JsonDict,
        passed: int,
        failed: int,
        warnings: int,
    ) -> tuple[int, int, int]:
        """Run key-nullability check and map status into aggregate counters."""
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


__all__ = ["SilverCheckExecutor"]
