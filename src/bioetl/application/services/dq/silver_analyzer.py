"""Silver layer DQ analyzer.

Coordinates Silver data quality monitoring by orchestrating:
- :class:`DQRuleEvaluator` for check execution
- :class:`DQThresholdCalculator` for error-rate thresholds
- :class:`DQReportFormatter` for final report serialization
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import polars as pl
import pyarrow as pa

from bioetl.application.services.dq.dq_report_formatter import DQReportFormatter
from bioetl.application.services.dq.dq_rule_evaluator import DQRuleEvaluator
from bioetl.application.services.dq.dq_threshold_calculator import DQThresholdCalculator
from bioetl.domain.ports import SilverDQConfigPort
from bioetl.domain.value_objects.dq_report import (
    ContentHashIntegrityResult,
    DeduplicationStatsResult,
    DQThresholds,
    NullRateResult,
    RecordCountResult,
    SchemaDriftResult,
    SilverDQReport,
    TypeConformanceResult,
    UniquenessResult,
    ValueDistributionResult,
)


class SilverDQAnalyzer:
    """Orchestrator for Silver layer DQ checks.

    Public API remains ``analyze(...)`` to preserve compatibility with
    ``SilverDQAnalyzerPort`` consumers.
    """

    def __init__(
        self,
        *,
        rule_evaluator: DQRuleEvaluator | None = None,
        threshold_calculator: DQThresholdCalculator | None = None,
        report_formatter: DQReportFormatter | None = None,
    ) -> None:
        self._rule_evaluator = rule_evaluator or DQRuleEvaluator()
        self._threshold_calculator = threshold_calculator or DQThresholdCalculator()
        self._report_formatter = report_formatter or DQReportFormatter()

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
        key_nullability_rules: list[
            dict[str, Any]  # Any: DQ rule definitions have heterogeneous values
        ]
        | None = None,
    ) -> SilverDQReport:
        """Analyze Silver data and generate DQ report."""
        if isinstance(data, pa.Table):
            df: pl.DataFrame = pl.from_arrow(data)  # type: ignore[assignment]
        else:
            df = data

        enabled_checks = set(config.get_checks_enums())
        checks, passed, failed, warnings = self._rule_evaluator.evaluate_checks(
            df=df,
            enabled_checks=enabled_checks,
            primary_keys=primary_keys,
            input_record_count=input_record_count,
            quarantined_count=quarantined_count,
            previous_schema=previous_schema,
            key_nullability_rules=key_nullability_rules or [],
        )
        checks = self._report_formatter.update_distribution_checks(checks)

        thresholds = self._threshold_calculator.calculate_thresholds(
            df_len=len(df),
            input_record_count=input_record_count,
            quarantined_count=quarantined_count,
            soft_fail_threshold=soft_fail_threshold,
            hard_fail_threshold=hard_fail_threshold,
        )

        return self._report_formatter.build_report(
            timestamp=timestamp,
            run_id=run_id,
            pipeline=pipeline,
            source_batch_ids=source_batch_ids,
            target_table=target_table,
            checks=checks,
            thresholds=thresholds,
            passed=passed,
            failed=failed,
            warnings=warnings,
        )

    # Compatibility helpers used by existing tests
    def _calculate_thresholds(
        self,
        df_len: int,
        input_record_count: int | None,
        quarantined_count: int,
        soft_fail_threshold: float,
        hard_fail_threshold: float,
    ) -> DQThresholds:
        return self._threshold_calculator.calculate_thresholds(
            df_len=df_len,
            input_record_count=input_record_count,
            quarantined_count=quarantined_count,
            soft_fail_threshold=soft_fail_threshold,
            hard_fail_threshold=hard_fail_threshold,
        )

    def _check_record_count(
        self,
        df: pl.DataFrame,
        input_count: int | None,
        quarantined_count: int,
    ) -> RecordCountResult:
        return self._rule_evaluator.check_record_count(
            df, input_count, quarantined_count
        )

    def _check_null_rates(self, df: pl.DataFrame) -> tuple[list[NullRateResult], float]:
        return self._rule_evaluator.check_null_rates(df)

    def _check_uniqueness(
        self, df: pl.DataFrame, primary_keys: list[str]
    ) -> UniquenessResult:
        return self._rule_evaluator.check_uniqueness(df, primary_keys)

    def _check_type_conformance(self, df: pl.DataFrame) -> TypeConformanceResult:
        return self._rule_evaluator.check_type_conformance(df)

    def _check_value_distribution(self, df: pl.DataFrame) -> ValueDistributionResult:
        return self._rule_evaluator.check_value_distribution(df)

    def _check_schema_drift(
        self, df: pl.DataFrame, previous_schema: dict[str, str] | None
    ) -> SchemaDriftResult:
        return self._rule_evaluator.check_schema_drift(df, previous_schema)

    def _check_deduplication(
        self,
        df: pl.DataFrame,
        primary_keys: list[str],
        input_count: int,
    ) -> DeduplicationStatsResult:
        return self._rule_evaluator.check_deduplication(df, primary_keys, input_count)

    def _check_content_hash_integrity(
        self, df: pl.DataFrame
    ) -> ContentHashIntegrityResult:
        return self._rule_evaluator.check_content_hash_integrity(df)

    def _check_key_nullability(
        self,
        df: pl.DataFrame,
        key_nullability_rules: list[
            dict[str, Any]  # Any: DQ check values vary by check type
        ],
    ) -> dict[str, Any]:  # Any: DQ check values vary by check type
        return self._rule_evaluator.check_key_nullability(df, key_nullability_rules)

    def _distribution_to_dict(
        self, result: ValueDistributionResult
    ) -> dict[str, Any]:  # Any: DQ check values vary by check type
        return self._report_formatter.format_distribution(result)


__all__ = [
    "DQReportFormatter",
    "DQRuleEvaluator",
    "DQThresholdCalculator",
    "SilverDQAnalyzer",
]
