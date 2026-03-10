"""Silver layer DQ analyzer orchestration facade."""

from __future__ import annotations

from datetime import datetime

import polars as pl
import pyarrow as pa

from bioetl.application.services.dq.silver_dq_report_assembler_service import (
    SilverDQReportAssemblerService,
)
from bioetl.application.services.dq.silver_dq_rule_evaluator_service import (
    DQRuleEvaluatorService,
)
from bioetl.application.services.dq.silver_dq_statistics_service import (
    SilverDQStatisticsService,
)
from bioetl.domain.ports import SilverDQConfigPort
from bioetl.domain.value_objects.dq_report import (
    ContentHashIntegrityResult,
    DeduplicationStatsResult,
    DQThresholds,
    NullRateResult,
    RecordCountResult,
    SchemaDriftResult,
    SilverDQCheckType,
    SilverDQReport,
    TypeConformanceResult,
    UniquenessResult,
    ValueDistributionResult,
)


class SilverDQAnalyzer:
    """Facade for Silver DQ analysis preserving existing public contract."""

    def __init__(
        self,
        evaluator_service: DQRuleEvaluatorService | None = None,
        statistics_service: SilverDQStatisticsService | None = None,
        report_assembler_service: SilverDQReportAssemblerService | None = None,
    ) -> None:
        self._statistics_service = statistics_service or SilverDQStatisticsService()
        self._evaluator_service = evaluator_service or DQRuleEvaluatorService(
            statistics_service=self._statistics_service
        )
        self._report_assembler_service = (
            report_assembler_service or SilverDQReportAssemblerService()
        )

    def _execute_checks(
        self,
        df: pl.DataFrame,
        enabled_checks: set[SilverDQCheckType],
        primary_keys: list[str],
        input_record_count: int | None,
        quarantined_count: int,
        previous_schema: dict[str, str] | None,
        key_nullability_rules: list[dict[str, object]] | None,
    ) -> tuple[dict[str, object], int, int, int]:
        """Backward-compatible wrapper around evaluator service."""
        return self._evaluator_service.execute_checks(
            df=df,
            enabled_checks=enabled_checks,
            primary_keys=primary_keys,
            input_record_count=input_record_count,
            quarantined_count=quarantined_count,
            previous_schema=previous_schema,
            key_nullability_rules=key_nullability_rules,
        )

    def _calculate_thresholds(
        self,
        df_len: int,
        input_record_count: int | None,
        quarantined_count: int,
        soft_fail_threshold: float,
        hard_fail_threshold: float,
    ) -> DQThresholds:
        """Backward-compatible wrapper around report assembler service."""
        return self._report_assembler_service.calculate_thresholds(
            df_len=df_len,
            input_record_count=input_record_count,
            quarantined_count=quarantined_count,
            soft_fail_threshold=soft_fail_threshold,
            hard_fail_threshold=hard_fail_threshold,
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
        key_nullability_rules: list[dict[str, object]] | None = None,
    ) -> SilverDQReport:
        """Analyze Silver data and generate DQ report."""
        if isinstance(data, pa.Table):
            df: pl.DataFrame = pl.from_arrow(data)  # type: ignore[assignment]
        else:
            df = data

        enabled_checks = set(config.get_checks_enums())
        checks, passed, failed, warnings = self._execute_checks(
            df=df,
            enabled_checks=enabled_checks,
            primary_keys=primary_keys,
            input_record_count=input_record_count,
            quarantined_count=quarantined_count,
            previous_schema=previous_schema,
            key_nullability_rules=key_nullability_rules,
        )

        thresholds = self._calculate_thresholds(
            df_len=len(df),
            input_record_count=input_record_count,
            quarantined_count=quarantined_count,
            soft_fail_threshold=soft_fail_threshold,
            hard_fail_threshold=hard_fail_threshold,
        )

        return self._report_assembler_service.assemble_report(
            run_id=run_id,
            pipeline=pipeline,
            target_table=target_table,
            source_batch_ids=source_batch_ids,
            timestamp=timestamp,
            checks=checks,
            thresholds=thresholds,
            passed=passed,
            failed=failed,
            warnings=warnings,
        )

    # Backward-compatible wrappers for existing unit tests and external callers.
    def _check_key_nullability(
        self,
        df: pl.DataFrame,
        key_nullability_rules: list[dict[str, object]],
    ) -> dict[str, object]:
        return self._evaluator_service.check_key_nullability(df, key_nullability_rules)

    def _check_record_count(
        self,
        df: pl.DataFrame,
        input_count: int | None,
        quarantined_count: int,
    ) -> RecordCountResult:
        return self._evaluator_service.check_record_count(
            df, input_count, quarantined_count
        )

    def _check_null_rates(self, df: pl.DataFrame) -> tuple[list[NullRateResult], float]:
        return self._evaluator_service.check_null_rates(df)

    def _check_uniqueness(
        self, df: pl.DataFrame, primary_keys: list[str]
    ) -> UniquenessResult:
        return self._evaluator_service.check_uniqueness(df, primary_keys)

    def _check_type_conformance(self, df: pl.DataFrame) -> TypeConformanceResult:
        return self._evaluator_service.check_type_conformance(df)

    def _check_value_distribution(self, df: pl.DataFrame) -> ValueDistributionResult:
        return self._statistics_service.check_value_distribution(df)

    def _check_schema_drift(
        self, df: pl.DataFrame, previous_schema: dict[str, str] | None
    ) -> SchemaDriftResult:
        return self._evaluator_service.check_schema_drift(df, previous_schema)

    def _check_deduplication(
        self,
        df: pl.DataFrame,
        primary_keys: list[str],
        input_count: int,
    ) -> DeduplicationStatsResult:
        return self._evaluator_service.check_deduplication(
            df, primary_keys, input_count
        )

    def _check_content_hash_integrity(
        self, df: pl.DataFrame
    ) -> ContentHashIntegrityResult:
        return self._evaluator_service.check_content_hash_integrity(df)

    def _distribution_to_dict(
        self, result: ValueDistributionResult
    ) -> dict[str, object]:
        return self._statistics_service.distribution_to_dict(result)


__all__ = ["SilverDQAnalyzer"]
