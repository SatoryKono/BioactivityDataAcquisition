"""Silver DQ rule evaluator orchestration service."""

from __future__ import annotations

import polars as pl

from bioetl.application.services.dq.dq_report_builders import update_counts
from bioetl.application.services.dq.silver_dq_checks_service import (
    SilverDQChecksService,
)
from bioetl.application.services.dq.silver_dq_statistics_service import (
    SilverDQStatisticsService,
)
from bioetl.domain.services.dq_serializer import to_dict
from bioetl.domain.value_objects.dq_report import (
    ContentHashIntegrityResult,
    DeduplicationStatsResult,
    DQCheckStatus,
    NullRateResult,
    RecordCountResult,
    SchemaDriftResult,
    SilverDQCheckType,
    TypeConformanceResult,
    UniquenessResult,
)


class DQRuleEvaluatorService:
    """Evaluate enabled checks and aggregate their statuses."""

    def __init__(
        self,
        checks_service: SilverDQChecksService | None = None,
        statistics_service: SilverDQStatisticsService | None = None,
    ) -> None:
        self._checks_service = checks_service or SilverDQChecksService()
        self._statistics_service = statistics_service or SilverDQStatisticsService()

    def execute_checks(
        self,
        df: pl.DataFrame,
        enabled_checks: set[SilverDQCheckType],
        primary_keys: list[str],
        input_record_count: int | None,
        quarantined_count: int,
        previous_schema: dict[str, str] | None,
        key_nullability_rules: list[dict[str, object]] | None,
    ) -> tuple[dict[str, object], int, int, int]:
        """Execute all enabled checks and collect check counters."""
        checks: dict[str, object] = {}
        passed, failed, warnings = 0, 0, 0

        if SilverDQCheckType.RECORD_COUNT in enabled_checks:
            record_count_result = self.check_record_count(
                df, input_record_count, quarantined_count
            )
            checks["record_count"] = to_dict(record_count_result)
            passed, failed, warnings = update_counts(
                record_count_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.NULL_RATE in enabled_checks:
            null_results, overall_rate = self.check_null_rates(df)
            checks["null_rate"] = {
                "columns": {r.column_name: to_dict(r) for r in null_results},
                "overall_null_rate": overall_rate,
                "status": DQCheckStatus.PASS.value,
            }
            passed += 1

        if SilverDQCheckType.UNIQUENESS in enabled_checks:
            uniqueness_result = self.check_uniqueness(df, primary_keys)
            checks["uniqueness"] = to_dict(uniqueness_result)
            passed, failed, warnings = update_counts(
                uniqueness_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.TYPE_CONFORMANCE in enabled_checks:
            conformance_result = self.check_type_conformance(df)
            checks["type_conformance"] = to_dict(conformance_result)
            passed, failed, warnings = update_counts(
                conformance_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.VALUE_DISTRIBUTION in enabled_checks:
            distribution_result = self._statistics_service.check_value_distribution(df)
            checks["value_distribution"] = (
                self._statistics_service.distribution_to_dict(distribution_result)
            )
            passed += 1

        if SilverDQCheckType.SCHEMA_DRIFT in enabled_checks:
            drift_result = self.check_schema_drift(df, previous_schema)
            checks["schema_drift"] = to_dict(drift_result)
            passed, failed, warnings = update_counts(
                drift_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.DEDUPLICATION_STATS in enabled_checks:
            deduplication_result = self.check_deduplication(
                df, primary_keys, input_record_count or len(df)
            )
            checks["deduplication_stats"] = to_dict(deduplication_result)
            passed, failed, warnings = update_counts(
                deduplication_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.CONTENT_HASH_INTEGRITY in enabled_checks:
            hash_integrity_result = self.check_content_hash_integrity(df)
            checks["content_hash_integrity"] = to_dict(hash_integrity_result)
            passed, failed, warnings = update_counts(
                hash_integrity_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.KEY_NULLABILITY in enabled_checks:
            key_nullability_result = self.check_key_nullability(
                df, key_nullability_rules or []
            )
            checks["key_nullability"] = key_nullability_result
            passed, failed, warnings = update_counts(
                DQCheckStatus(str(key_nullability_result["status"])),
                passed,
                failed,
                warnings,
            )

        return checks, passed, failed, warnings

    def check_key_nullability(
        self,
        df: pl.DataFrame,
        key_nullability_rules: list[dict[str, object]],
    ) -> dict[str, object]:
        return self._checks_service.check_key_nullability(df, key_nullability_rules)

    def check_record_count(
        self,
        df: pl.DataFrame,
        input_count: int | None,
        quarantined_count: int,
    ) -> RecordCountResult:
        return self._checks_service.check_record_count(
            df, input_count, quarantined_count
        )

    def check_null_rates(self, df: pl.DataFrame) -> tuple[list[NullRateResult], float]:
        return self._checks_service.check_null_rates(df)

    def check_uniqueness(
        self, df: pl.DataFrame, primary_keys: list[str]
    ) -> UniquenessResult:
        return self._checks_service.check_uniqueness(df, primary_keys)

    def check_type_conformance(self, df: pl.DataFrame) -> TypeConformanceResult:
        return self._checks_service.check_type_conformance(df)

    def check_schema_drift(
        self, df: pl.DataFrame, previous_schema: dict[str, str] | None
    ) -> SchemaDriftResult:
        return self._checks_service.check_schema_drift(df, previous_schema)

    def check_deduplication(
        self,
        df: pl.DataFrame,
        _primary_keys: list[str],
        input_count: int,
    ) -> DeduplicationStatsResult:
        return self._checks_service.check_deduplication(df, input_count)

    def check_content_hash_integrity(
        self, df: pl.DataFrame
    ) -> ContentHashIntegrityResult:
        return self._checks_service.check_content_hash_integrity(df)


__all__ = ["DQRuleEvaluatorService"]
