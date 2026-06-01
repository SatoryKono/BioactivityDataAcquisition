"""Direct unit tests for ``silver_check_executor``."""

from __future__ import annotations

import pytest

from unittest.mock import MagicMock

import polars as pl

from bioetl.application.services.dq.silver_check_executor import SilverCheckExecutor
from bioetl.domain.types import DriftLevel
from bioetl.domain.value_objects.dq_report import (
    ContentHashIntegrityResult,
    DQCheckStatus,
    DeduplicationStatsResult,
    NullRateResult,
    RecordCountResult,
    SchemaDriftResult,
    SilverDQCheckType,
    TypeConformanceResult,
    UniquenessResult,
)


pytestmark = pytest.mark.unit

def _build_executor() -> tuple[SilverCheckExecutor, MagicMock, MagicMock]:
    statistics = MagicMock()
    threshold_checker = MagicMock()
    return (
        SilverCheckExecutor(
            statistics=statistics,
            threshold_checker=threshold_checker,
        ),
        statistics,
        threshold_checker,
    )


class TestSilverCheckExecutorDirect:
    """Direct ownership tests for ``SilverCheckExecutor``."""

    def test_execute_checks_aggregates_standard_and_custom_statuses(self) -> None:
        executor, statistics, threshold_checker = _build_executor()
        df = pl.DataFrame({"id": [1, 2], "_content_hash": ["a", "b"]})

        statistics.check_record_count.return_value = RecordCountResult(
            value=2,
            input_records=3,
            output_records=2,
            quarantined_records=1,
            quarantine_rate=0.3333,
            status=DQCheckStatus.PASS,
        )
        statistics.check_null_rates.return_value = (
            [
                NullRateResult(
                    column_name="id", null_rate=0.0, status=DQCheckStatus.PASS
                )
            ],
            0.0,
        )
        distribution_payload = {"status": "pass", "numeric_columns": {}}
        statistics.check_value_distribution.return_value = object()
        statistics.distribution_to_dict.return_value = distribution_payload
        threshold_checker.check_key_nullability.return_value = {
            "status": DQCheckStatus.WARN.value,
            "violations": [],
        }

        checks, passed, failed, warnings = executor.execute_checks(
            df=df,
            enabled_checks={
                SilverDQCheckType.RECORD_COUNT,
                SilverDQCheckType.NULL_RATE,
                SilverDQCheckType.VALUE_DISTRIBUTION,
                SilverDQCheckType.KEY_NULLABILITY,
            },
            primary_keys=["id"],
            input_record_count=3,
            quarantined_count=1,
            previous_schema={"id": "Int64"},
            key_nullability_rules=[{"column": "id"}],
        )

        assert checks["record_count"]["status"] == DQCheckStatus.PASS.value
        assert checks["null_rate"]["status"] == DQCheckStatus.PASS.value
        assert checks["value_distribution"] == distribution_payload
        assert checks["key_nullability"]["status"] == DQCheckStatus.WARN.value
        assert (passed, failed, warnings) == (3, 0, 1)

    def test_execute_checks_passes_empty_rules_list_when_none_provided(self) -> None:
        executor, _statistics, threshold_checker = _build_executor()
        df = pl.DataFrame({"id": [1]})
        threshold_checker.check_key_nullability.return_value = {
            "status": DQCheckStatus.PASS.value,
            "violations": [],
        }

        checks, passed, failed, warnings = executor.execute_checks(
            df=df,
            enabled_checks={SilverDQCheckType.KEY_NULLABILITY},
            primary_keys=["id"],
            input_record_count=None,
            quarantined_count=0,
            previous_schema=None,
            key_nullability_rules=None,
        )

        threshold_checker.check_key_nullability.assert_called_once_with(df, [])
        assert checks["key_nullability"]["status"] == DQCheckStatus.PASS.value
        assert (passed, failed, warnings) == (1, 0, 0)

    def test_deduplication_uses_dataframe_length_when_input_count_missing(self) -> None:
        executor, statistics, _threshold_checker = _build_executor()
        df = pl.DataFrame({"id": [1, 2, 3]})

        statistics.check_deduplication.return_value = DeduplicationStatsResult(
            input_before_dedupe=3,
            duplicates_by_content_hash=0,
            duplicates_by_business_key=0,
            output_after_dedupe=3,
            status=DQCheckStatus.PASS,
        )

        checks, passed, failed, warnings = executor.execute_checks(
            df=df,
            enabled_checks={SilverDQCheckType.DEDUPLICATION_STATS},
            primary_keys=["id"],
            input_record_count=None,
            quarantined_count=0,
            previous_schema=None,
            key_nullability_rules=None,
        )

        statistics.check_deduplication.assert_called_once_with(df, ["id"], 3)
        assert checks["deduplication_stats"]["status"] == DQCheckStatus.PASS.value
        assert (passed, failed, warnings) == (1, 0, 0)

    def test_standard_checks_preserve_fail_and_warn_counts(self) -> None:
        executor, statistics, _threshold_checker = _build_executor()
        df = pl.DataFrame({"id": [1], "_content_hash": ["hash"]})

        statistics.check_uniqueness.return_value = UniquenessResult(
            primary_key="id",
            unique_count=0,
            total_count=1,
            duplicate_rate=1.0,
            status=DQCheckStatus.WARN,
        )
        statistics.check_type_conformance.return_value = TypeConformanceResult(
            schema_version="v1",
            pandera_passed=False,
            errors=("bad type",),
            status=DQCheckStatus.FAIL,
        )
        statistics.check_schema_drift.return_value = SchemaDriftResult(
            drift_level=DriftLevel.INFO,
            status=DQCheckStatus.PASS,
        )
        statistics.check_content_hash_integrity.return_value = (
            ContentHashIntegrityResult(
                records_checked=1,
                hash_collisions=0,
                rehash_mismatches=0,
                status=DQCheckStatus.PASS,
            )
        )

        checks, passed, failed, warnings = executor.execute_checks(
            df=df,
            enabled_checks={
                SilverDQCheckType.UNIQUENESS,
                SilverDQCheckType.TYPE_CONFORMANCE,
                SilverDQCheckType.SCHEMA_DRIFT,
                SilverDQCheckType.CONTENT_HASH_INTEGRITY,
            },
            primary_keys=["id"],
            input_record_count=None,
            quarantined_count=0,
            previous_schema={"id": "Int64"},
            key_nullability_rules=None,
        )

        assert set(checks) == {
            "uniqueness",
            "type_conformance",
            "schema_drift",
            "content_hash_integrity",
        }
        assert checks["uniqueness"]["status"] == DQCheckStatus.WARN.value
        assert checks["type_conformance"]["status"] == DQCheckStatus.FAIL.value
        assert (passed, failed, warnings) == (2, 1, 1)
