"""Silver DQ rule evaluation component."""

from __future__ import annotations

from typing import Any

import polars as pl

from bioetl.application.services.dq.dq_report_builders import update_counts
from bioetl.application.services.dq.dq_rule_checks import (
    check_content_hash_integrity,
    check_deduplication,
    check_key_nullability,
    check_null_rates,
    check_record_count,
    check_schema_drift,
    check_type_conformance,
    check_uniqueness,
    check_value_distribution,
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
    ValueDistributionResult,
)


class DQRuleEvaluator:
    """Evaluate Silver DQ checks and collect serialized check output."""

    def evaluate_checks(
        self,
        *,
        df: pl.DataFrame,
        enabled_checks: set[SilverDQCheckType],
        primary_keys: list[str],
        input_record_count: int | None,
        quarantined_count: int,
        previous_schema: dict[str, str] | None,
        key_nullability_rules: list[
            dict[str, Any]  # Any: DQ rule definitions have heterogeneous values
        ],
    ) -> tuple[
        dict[str, Any], int, int, int  # Any: DQ check values vary by check type
    ]:
        """Execute enabled checks and return check payload + summary counters."""
        checks: dict[str, Any] = {}
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
            checks["value_distribution"] = self.check_value_distribution(df)
            passed += 1

        if SilverDQCheckType.SCHEMA_DRIFT in enabled_checks:
            drift_result = self.check_schema_drift(df, previous_schema)
            checks["schema_drift"] = to_dict(drift_result)
            passed, failed, warnings = update_counts(
                drift_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.DEDUPLICATION_STATS in enabled_checks:
            dedup_result = self.check_deduplication(
                df, primary_keys, input_record_count or len(df)
            )
            checks["deduplication_stats"] = to_dict(dedup_result)
            passed, failed, warnings = update_counts(
                dedup_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.CONTENT_HASH_INTEGRITY in enabled_checks:
            hash_result = self.check_content_hash_integrity(df)
            checks["content_hash_integrity"] = to_dict(hash_result)
            passed, failed, warnings = update_counts(
                hash_result.status, passed, failed, warnings
            )

        if SilverDQCheckType.KEY_NULLABILITY in enabled_checks:
            key_nullability_result = self.check_key_nullability(
                df, key_nullability_rules
            )
            checks["key_nullability"] = key_nullability_result
            passed, failed, warnings = update_counts(
                DQCheckStatus(key_nullability_result["status"]),
                passed,
                failed,
                warnings,
            )

        return checks, passed, failed, warnings

    def check_key_nullability(
        self,
        df: pl.DataFrame,
        key_nullability_rules: list[
            dict[str, Any]  # Any: DQ check values vary by check type
        ],
    ) -> dict[str, Any]:  # Any: DQ check values vary by check type
        return check_key_nullability(df, key_nullability_rules)

    def check_record_count(
        self,
        df: pl.DataFrame,
        input_count: int | None,
        quarantined_count: int,
    ) -> RecordCountResult:
        return check_record_count(df, input_count, quarantined_count)

    def check_null_rates(self, df: pl.DataFrame) -> tuple[list[NullRateResult], float]:
        return check_null_rates(df)

    def check_uniqueness(
        self, df: pl.DataFrame, primary_keys: list[str]
    ) -> UniquenessResult:
        return check_uniqueness(df, primary_keys)

    def check_type_conformance(self, df: pl.DataFrame) -> TypeConformanceResult:
        return check_type_conformance(df)

    def check_value_distribution(self, df: pl.DataFrame) -> ValueDistributionResult:
        return check_value_distribution(df)

    def check_schema_drift(
        self, df: pl.DataFrame, previous_schema: dict[str, str] | None
    ) -> SchemaDriftResult:
        return check_schema_drift(df, previous_schema)

    def check_deduplication(
        self,
        df: pl.DataFrame,
        primary_keys: list[str],
        input_count: int,
    ) -> DeduplicationStatsResult:
        return check_deduplication(df, primary_keys, input_count)

    def check_content_hash_integrity(
        self, df: pl.DataFrame
    ) -> ContentHashIntegrityResult:
        return check_content_hash_integrity(df)


__all__ = ["DQRuleEvaluator"]
