"""Unit tests for SilverDQAnalyzer.

Tests for SilverDQAnalyzer comprehensive data quality checks:
- Record count analysis with quarantine tracking
- Null rate per column and overall
- Uniqueness / duplicate detection
- Type conformance checks
- Value distribution (numeric and categorical)
- Schema drift detection
- Deduplication statistics
- Content hash integrity
- Key nullability rules
- Threshold calculation (PASS / WARN / FAIL)
- PyArrow → Polars conversion in analyze()
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import polars as pl
import pyarrow as pa
import pytest

from bioetl.application.services.dq.silver_check_executor import SilverCheckExecutor
from bioetl.application.services.dq.silver_analyzer import SilverDQAnalyzer
from bioetl.application.services.dq.silver_statistics import SilverStatisticsCalculator
from bioetl.application.services.dq.silver_threshold import SilverThresholdChecker
from bioetl.domain.ports import SilverDQAnalyzeRequest
from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    MedallionLayer,
    SilverDQCheckType,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _build_analyzer() -> SilverDQAnalyzer:
    """Create a fully wired SilverDQAnalyzer for unit tests."""
    statistics = SilverStatisticsCalculator()
    threshold_checker = SilverThresholdChecker()
    check_executor = SilverCheckExecutor(
        statistics=statistics,
        threshold_checker=threshold_checker,
    )
    return SilverDQAnalyzer(
        statistics=statistics,
        threshold_checker=threshold_checker,
        check_executor=check_executor,
    )


@pytest.fixture()
def analyzer() -> SilverDQAnalyzer:
    """Create SilverDQAnalyzer instance."""
    return _build_analyzer()


@pytest.fixture()
def simple_df() -> pl.DataFrame:
    """A small well-formed Silver DataFrame."""
    return pl.DataFrame(
        {
            "_content_hash": ["hash_a", "hash_b", "hash_c"],
            "record_id": [1, 2, 3],
            "name": ["alpha", "beta", "gamma"],
            "value": [10.0, 20.0, 30.0],
        }
    )


@pytest.fixture()
def mock_config_all_checks() -> MagicMock:
    """Config mock that enables all Silver DQ check types."""
    config = MagicMock()
    config.get_checks_enums.return_value = list(SilverDQCheckType)
    return config


@pytest.fixture()
def mock_config_empty() -> MagicMock:
    """Config mock that enables no checks (empty set)."""
    config = MagicMock()
    config.get_checks_enums.return_value = []
    return config


# ---------------------------------------------------------------------------
# _calculate_thresholds
# ---------------------------------------------------------------------------


class TestCalculateThresholds:
    """Tests for _calculate_thresholds helper."""

    def test_pass_status_no_quarantined(self, analyzer: SilverDQAnalyzer) -> None:
        """No quarantined records → PASS."""
        result = analyzer._threshold.calculate_thresholds(
            df_len=100,
            input_record_count=100,
            quarantined_count=0,
            soft_fail_threshold=0.05,
            hard_fail_threshold=0.20,
        )
        assert result.threshold_status == DQCheckStatus.PASS
        assert result.current_error_rate == pytest.approx(0.0)

    def test_warn_status_at_soft_threshold(self, analyzer: SilverDQAnalyzer) -> None:
        """Error rate at soft threshold → WARN."""
        result = analyzer._threshold.calculate_thresholds(
            df_len=95,
            input_record_count=100,
            quarantined_count=10,  # 10% error rate ≥ 5% → WARN
            soft_fail_threshold=0.05,
            hard_fail_threshold=0.20,
        )
        assert result.threshold_status == DQCheckStatus.WARN
        assert result.current_error_rate == pytest.approx(0.1)

    def test_fail_status_at_hard_threshold(self, analyzer: SilverDQAnalyzer) -> None:
        """Error rate at hard threshold → FAIL."""
        result = analyzer._threshold.calculate_thresholds(
            df_len=80,
            input_record_count=100,
            quarantined_count=25,  # 25% ≥ 20% → FAIL
            soft_fail_threshold=0.05,
            hard_fail_threshold=0.20,
        )
        assert result.threshold_status == DQCheckStatus.FAIL

    def test_input_count_none_uses_df_len_plus_quarantine(
        self, analyzer: SilverDQAnalyzer
    ) -> None:
        """When input_record_count is None, total = df_len + quarantined_count."""
        result = analyzer._threshold.calculate_thresholds(
            df_len=90,
            input_record_count=None,
            quarantined_count=10,  # total=100, rate=0.10
            soft_fail_threshold=0.05,
            hard_fail_threshold=0.20,
        )
        assert result.current_error_rate == pytest.approx(0.1)
        assert result.threshold_status == DQCheckStatus.WARN

    def test_zero_total_no_division_error(self, analyzer: SilverDQAnalyzer) -> None:
        """total_input=0 → error_rate=0.0, no ZeroDivisionError."""
        result = analyzer._threshold.calculate_thresholds(
            df_len=0,
            input_record_count=0,
            quarantined_count=0,
            soft_fail_threshold=0.05,
            hard_fail_threshold=0.20,
        )
        assert result.current_error_rate == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _check_record_count
# ---------------------------------------------------------------------------


class TestCheckRecordCount:
    """Tests for record count check."""

    def test_pass_no_quarantine(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"id": [1, 2, 3]})
        result = analyzer._statistics.check_record_count(df, None, 0)
        assert result.status == DQCheckStatus.PASS
        assert result.output_records == 3
        assert result.quarantine_rate == pytest.approx(0.0)

    def test_warn_high_quarantine_rate(self, analyzer: SilverDQAnalyzer) -> None:
        """More than 10% quarantined → WARN."""
        df = pl.DataFrame({"id": [1, 2, 3, 4, 5, 6, 7, 8, 9]})
        result = analyzer._statistics.check_record_count(df, 10, 2)  # 20% quarantined
        assert result.status == DQCheckStatus.WARN
        assert result.quarantined_records == 2

    def test_input_count_explicit(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"id": [1, 2, 3]})
        result = analyzer._statistics.check_record_count(df, 10, 0)
        assert result.input_records == 10
        assert result.output_records == 3


# ---------------------------------------------------------------------------
# _check_null_rates
# ---------------------------------------------------------------------------


class TestCheckNullRates:
    """Tests for null rate calculation."""

    def test_no_nulls(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        results, overall = analyzer._statistics.check_null_rates(df)
        assert overall == pytest.approx(0.0)
        assert all(r.null_rate == pytest.approx(0.0) for r in results)
        assert all(r.status == DQCheckStatus.PASS for r in results)

    def test_column_with_high_null_rate_warns(self, analyzer: SilverDQAnalyzer) -> None:
        """Column with >50% nulls → WARN."""
        df = pl.DataFrame({"a": [1, None, None]})
        results, overall = analyzer._statistics.check_null_rates(df)
        assert results[0].status == DQCheckStatus.WARN
        assert results[0].null_rate > 0.5

    def test_overall_rate_calculation(self, analyzer: SilverDQAnalyzer) -> None:
        """Overall rate is total nulls / total cells."""
        df = pl.DataFrame({"a": [None, None], "b": [1, 1]})  # 2 nulls / 4 cells = 0.5
        _, overall = analyzer._statistics.check_null_rates(df)
        assert overall == pytest.approx(0.5)

    def test_empty_dataframe(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"a": pl.Series([], dtype=pl.Int64)})
        results, overall = analyzer._statistics.check_null_rates(df)
        assert overall == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _check_uniqueness
# ---------------------------------------------------------------------------


class TestCheckUniqueness:
    """Tests for uniqueness / duplicate check."""

    def test_unique_records_pass(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"id": [1, 2, 3]})
        result = analyzer._statistics.check_uniqueness(df, ["id"])
        assert result.status == DQCheckStatus.PASS
        assert result.duplicate_rate == pytest.approx(0.0)

    def test_duplicates_warn(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"id": [1, 1, 2]})
        result = analyzer._statistics.check_uniqueness(df, ["id"])
        assert result.status == DQCheckStatus.WARN
        assert result.duplicate_rate > 0

    def test_no_primary_keys_pass(self, analyzer: SilverDQAnalyzer) -> None:
        """Empty primary_keys list → PASS with no duplicate check."""
        df = pl.DataFrame({"id": [1, 1, 1]})
        result = analyzer._statistics.check_uniqueness(df, [])
        assert result.status == DQCheckStatus.PASS
        assert result.primary_key == ""

    def test_missing_primary_key_column_warn(self, analyzer: SilverDQAnalyzer) -> None:
        """Primary key column not in DataFrame → WARN."""
        df = pl.DataFrame({"id": [1, 2, 3]})
        result = analyzer._statistics.check_uniqueness(df, ["nonexistent_column"])
        assert result.status == DQCheckStatus.WARN

    def test_column_cardinality_stats(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"id": [1, 2, 3], "category": ["a", "b", "a"]})
        result = analyzer._statistics.check_uniqueness(df, ["id"])
        # Column stats computed for first 10 columns
        assert "id" in result.column_stats
        assert result.column_stats["id"]["cardinality"] == 3


# ---------------------------------------------------------------------------
# _check_type_conformance
# ---------------------------------------------------------------------------


class TestCheckTypeConformance:
    """Tests for type conformance check."""

    def test_pass_normal_types(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"id": [1, 2], "name": ["a", "b"], "v": [1.0, 2.0]})
        result = analyzer._statistics.check_type_conformance(df)
        assert result.status == DQCheckStatus.PASS
        assert result.pandera_passed is True

    def test_warn_object_column(self, analyzer: SilverDQAnalyzer) -> None:
        """Object dtype column → type error → WARN status."""
        df = pl.DataFrame({"mixed": pl.Series([1, "str"], dtype=pl.Object)})
        result = analyzer._statistics.check_type_conformance(df)
        assert result.status == DQCheckStatus.WARN
        assert result.pandera_passed is False
        assert len(result.errors) > 0


# ---------------------------------------------------------------------------
# _check_value_distribution
# ---------------------------------------------------------------------------


class TestCheckValueDistribution:
    """Tests for value distribution profiling."""

    def test_numeric_columns_profiled(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"score": [1.0, 2.0, 3.0, 4.0, 5.0]})
        result = analyzer._statistics.check_value_distribution(df)
        assert "score" in result.numeric_columns
        stat = result.numeric_columns["score"]
        assert stat.min == pytest.approx(1.0)
        assert stat.max == pytest.approx(5.0)
        assert stat.mean == pytest.approx(3.0)

    def test_categorical_columns_profiled(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"category": ["a", "b", "a", "c", "b", "a"]})
        result = analyzer._statistics.check_value_distribution(df)
        assert "category" in result.categorical_columns
        cat = result.categorical_columns["category"]
        assert cat.cardinality == 3
        assert len(cat.top_values) <= 5

    def test_status_always_pass(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"id": [1, 2, 3]})
        result = analyzer._statistics.check_value_distribution(df)
        assert result.status == DQCheckStatus.PASS

    def test_empty_numeric_column_skipped(self, analyzer: SilverDQAnalyzer) -> None:
        """Numeric column with all nulls: no crash."""
        df = pl.DataFrame({"v": pl.Series([None, None], dtype=pl.Float64)})
        result = analyzer._statistics.check_value_distribution(df)
        # Empty stats column — may be empty or may have None fields; no exception
        assert result.status == DQCheckStatus.PASS

    def test_limits_to_20_columns(self, analyzer: SilverDQAnalyzer) -> None:
        """Only first 20 columns are profiled."""
        data = {f"col_{i}": [i * 1.0, i * 2.0] for i in range(25)}
        df = pl.DataFrame(data)
        result = analyzer._statistics.check_value_distribution(df)
        total_profiled = len(result.numeric_columns) + len(result.categorical_columns)
        assert total_profiled <= 20


# ---------------------------------------------------------------------------
# _check_schema_drift
# ---------------------------------------------------------------------------


class TestCheckSchemaDrift:
    """Tests for schema drift detection."""

    def test_no_previous_schema_info(self, analyzer: SilverDQAnalyzer) -> None:
        """First run (no previous schema) → INFO, PASS."""
        from bioetl.domain.value_objects.dq_report import DriftLevel

        df = pl.DataFrame({"id": [1, 2], "name": ["a", "b"]})
        result = analyzer._statistics.check_schema_drift(df, None)
        assert result.drift_level == DriftLevel.INFO
        assert result.status == DQCheckStatus.PASS

    def test_no_drift_same_schema(self, analyzer: SilverDQAnalyzer) -> None:
        from bioetl.domain.value_objects.dq_report import DriftLevel

        df = pl.DataFrame({"id": [1, 2], "name": ["a", "b"]})
        previous = {"id": "Int64", "name": "String"}
        result = analyzer._statistics.check_schema_drift(df, previous)
        assert result.drift_level == DriftLevel.INFO
        assert result.status == DQCheckStatus.PASS
        assert len(result.new_fields) == 0
        assert len(result.missing_fields) == 0

    def test_new_field_added_info(self, analyzer: SilverDQAnalyzer) -> None:
        from bioetl.domain.value_objects.dq_report import DriftLevel

        df = pl.DataFrame({"id": [1], "name": ["a"], "extra": [42]})
        previous = {"id": "Int64", "name": "String"}
        result = analyzer._statistics.check_schema_drift(df, previous)
        assert result.drift_level == DriftLevel.INFO
        assert "extra" in result.new_fields

    def test_missing_field_critical_warn(self, analyzer: SilverDQAnalyzer) -> None:
        from bioetl.domain.value_objects.dq_report import DriftLevel

        df = pl.DataFrame({"id": [1]})
        previous = {"id": "Int64", "name": "String"}
        result = analyzer._statistics.check_schema_drift(df, previous)
        assert result.drift_level == DriftLevel.CRITICAL
        assert result.status == DQCheckStatus.WARN
        assert "name" in result.missing_fields

    def test_type_change_critical_warn(self, analyzer: SilverDQAnalyzer) -> None:
        from bioetl.domain.value_objects.dq_report import DriftLevel

        df = pl.DataFrame({"id": pl.Series([1, 2], dtype=pl.Float64)})
        previous = {"id": "Int64"}
        result = analyzer._statistics.check_schema_drift(df, previous)
        assert result.drift_level == DriftLevel.CRITICAL
        assert len(result.type_changes) > 0


# ---------------------------------------------------------------------------
# _check_deduplication
# ---------------------------------------------------------------------------


class TestCheckDeduplication:
    """Tests for deduplication statistics."""

    def test_no_duplication(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"id": [1, 2, 3]})
        result = analyzer._statistics.check_deduplication(df, ["id"], 3)
        assert result.output_after_dedupe == 3
        assert result.input_before_dedupe == 3
        assert result.status == DQCheckStatus.PASS

    def test_with_input_larger_than_output(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"id": [1, 2, 3]})
        result = analyzer._statistics.check_deduplication(df, ["id"], 10)
        assert result.input_before_dedupe == 10
        assert result.output_after_dedupe == 3

    def test_content_hash_duplicates_counted(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame(
            {
                "_content_hash": ["hash_a", "hash_a", "hash_b"],
                "id": [1, 2, 3],
            }
        )
        result = analyzer._statistics.check_deduplication(df, ["id"], 3)
        assert result.duplicates_by_content_hash == 1  # 3 records - 2 unique hashes

    def test_no_content_hash_column(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"id": [1, 2, 3]})
        result = analyzer._statistics.check_deduplication(df, ["id"], 5)
        assert result.duplicates_by_content_hash == 0


# ---------------------------------------------------------------------------
# _check_content_hash_integrity
# ---------------------------------------------------------------------------


class TestCheckContentHashIntegrity:
    """Tests for content hash integrity check."""

    def test_no_hash_column_pass(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"id": [1, 2, 3]})
        result = analyzer._statistics.check_content_hash_integrity(df)
        assert result.status == DQCheckStatus.PASS
        assert result.records_checked == 0

    def test_unique_hashes_pass(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"_content_hash": ["a", "b", "c"], "id": [1, 2, 3]})
        result = analyzer._statistics.check_content_hash_integrity(df)
        assert result.status == DQCheckStatus.PASS
        assert result.hash_collisions == 0
        assert result.records_checked == 3

    def test_duplicate_hashes_warn(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"_content_hash": ["a", "a", "b"], "id": [1, 2, 3]})
        result = analyzer._statistics.check_content_hash_integrity(df)
        assert result.status == DQCheckStatus.WARN
        assert result.hash_collisions > 0


# ---------------------------------------------------------------------------
# _check_key_nullability
# ---------------------------------------------------------------------------


class TestCheckKeyNullability:
    """Tests for key nullability rules enforcement."""

    def test_no_rules_pass(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"id": [1, 2, None]})
        result = analyzer._threshold.check_key_nullability(df, [])
        assert result["status"] == DQCheckStatus.PASS.value
        assert result["violations"] == []

    def test_nullable_rule_skipped(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"id": [1, None, 3]})
        rules = [{"field": "id", "key_type": "merge", "nullable": True}]
        result = analyzer._threshold.check_key_nullability(df, rules)
        assert result["status"] == DQCheckStatus.PASS.value
        assert result["violations"] == []

    def test_non_nullable_violation_fail(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"id": [1, None, 3]})
        rules = [{"field": "id", "key_type": "merge", "nullable": False}]
        result = analyzer._threshold.check_key_nullability(df, rules)
        assert result["status"] == DQCheckStatus.FAIL.value
        assert len(result["violations"]) == 1
        assert result["violations"][0]["field"] == "id"
        assert result["violations"][0]["null_count"] == 1

    def test_missing_column_skipped(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"other": [1, 2, 3]})
        rules = [{"field": "id", "key_type": "merge", "nullable": False}]
        result = analyzer._threshold.check_key_nullability(df, rules)
        assert result["status"] == DQCheckStatus.PASS.value

    def test_rules_checked_count(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"id": [1, 2, 3], "key": ["a", "b", "c"]})
        rules = [
            {"field": "id", "key_type": "merge", "nullable": False},
            {"field": "key", "key_type": "partition", "nullable": False},
        ]
        result = analyzer._threshold.check_key_nullability(df, rules)
        assert result["rules_checked"] == 2


# ---------------------------------------------------------------------------
# analyze() — integration
# ---------------------------------------------------------------------------


class TestAnalyze:
    """Integration tests for the main analyze() method."""

    def test_analyze_with_polars_dataframe(
        self,
        analyzer: SilverDQAnalyzer,
        simple_df: pl.DataFrame,
        mock_config_all_checks: MagicMock,
    ) -> None:
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        report = analyzer.analyze(
            data=simple_df,
            run_id="test-run-001",
            pipeline="chembl.compound",
            target_table="silver/chembl/compound",
            source_batch_ids=["batch-001"],
            config=mock_config_all_checks,
            timestamp=ts,
            primary_keys=["record_id"],
        )
        assert report.layer == MedallionLayer.SILVER
        assert report.run_id == "test-run-001"
        assert report.pipeline == "chembl.compound"
        assert report.summary is not None

    def test_analyze_with_pyarrow_table(
        self,
        analyzer: SilverDQAnalyzer,
        mock_config_all_checks: MagicMock,
    ) -> None:
        """PyArrow Table should be converted to Polars before processing."""
        table = pa.table(
            {
                "id": [1, 2, 3],
                "name": ["a", "b", "c"],
                "_content_hash": ["h1", "h2", "h3"],
            }
        )
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        report = analyzer.analyze(
            data=table,
            run_id="arrow-run",
            pipeline="test",
            target_table="silver/test",
            source_batch_ids=["batch-arrow"],
            config=mock_config_all_checks,
            timestamp=ts,
            primary_keys=["id"],
        )
        assert report.layer == MedallionLayer.SILVER
        assert "record_count" in report.checks

    def test_analyze_with_request_bundle(
        self,
        analyzer: SilverDQAnalyzer,
        simple_df: pl.DataFrame,
        mock_config_all_checks: MagicMock,
    ) -> None:
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        request = SilverDQAnalyzeRequest(
            data=simple_df,
            run_id="request-run",
            pipeline="chembl.compound",
            target_table="silver/chembl/compound",
            source_batch_ids=["batch-request"],
            config=mock_config_all_checks,
            timestamp=ts,
            primary_keys=["record_id"],
        )

        report = analyzer.analyze(request)

        assert report.layer == MedallionLayer.SILVER
        assert report.run_id == "request-run"
        assert report.source_batch_ids == ("batch-request",)

    def test_analyze_no_checks_enabled(
        self,
        analyzer: SilverDQAnalyzer,
        simple_df: pl.DataFrame,
        mock_config_empty: MagicMock,
    ) -> None:
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        report = analyzer.analyze(
            data=simple_df,
            run_id="empty-checks",
            pipeline="test",
            target_table="silver/test",
            source_batch_ids=[],
            config=mock_config_empty,
            timestamp=ts,
            primary_keys=[],
        )
        assert report.checks == {}
        assert report.summary.passed == 0
        assert report.summary.failed == 0

    def test_analyze_with_quarantined_records_triggers_warn(
        self,
        analyzer: SilverDQAnalyzer,
        mock_config_empty: MagicMock,
    ) -> None:
        df = pl.DataFrame({"id": [1, 2, 3, 4, 5]})
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        report = analyzer.analyze(
            data=df,
            run_id="quarantine-test",
            pipeline="test",
            target_table="silver/test",
            source_batch_ids=["batch-q"],
            config=mock_config_empty,
            timestamp=ts,
            primary_keys=["id"],
            input_record_count=100,
            quarantined_count=10,  # 10% quarantined → ≥5% soft, <20% hard → WARN
        )
        assert report.thresholds.threshold_status == DQCheckStatus.WARN

    def test_analyze_hard_fail_threshold(
        self,
        analyzer: SilverDQAnalyzer,
        mock_config_empty: MagicMock,
    ) -> None:
        df = pl.DataFrame({"id": [1, 2]})
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        report = analyzer.analyze(
            data=df,
            run_id="hard-fail",
            pipeline="test",
            target_table="silver/test",
            source_batch_ids=[],
            config=mock_config_empty,
            timestamp=ts,
            primary_keys=[],
            input_record_count=10,
            quarantined_count=3,  # 30% → FAIL (hard_fail_threshold=0.20)
        )
        assert report.thresholds.threshold_status == DQCheckStatus.FAIL

    def test_analyze_with_previous_schema_drift_detection(
        self,
        analyzer: SilverDQAnalyzer,
        mock_config_all_checks: MagicMock,
    ) -> None:
        """Schema drift check is triggered when previous_schema provided."""
        df = pl.DataFrame({"id": [1, 2], "new_col": ["x", "y"]})
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        previous = {"id": "Int64"}  # new_col is missing from previous

        report = analyzer.analyze(
            data=df,
            run_id="drift-test",
            pipeline="test",
            target_table="silver/test",
            source_batch_ids=["b1"],
            config=mock_config_all_checks,
            timestamp=ts,
            primary_keys=["id"],
            previous_schema=previous,
        )
        assert "schema_drift" in report.checks

    def test_analyze_key_nullability_rules(
        self,
        analyzer: SilverDQAnalyzer,
        mock_config_all_checks: MagicMock,
    ) -> None:
        df = pl.DataFrame({"merge_key": [1, None, 3]})
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        rules = [{"field": "merge_key", "key_type": "merge", "nullable": False}]

        report = analyzer.analyze(
            data=df,
            run_id="key-null-test",
            pipeline="test",
            target_table="silver/test",
            source_batch_ids=[],
            config=mock_config_all_checks,
            timestamp=ts,
            primary_keys=["merge_key"],
            key_nullability_rules=rules,
        )
        assert "key_nullability" in report.checks
        assert report.checks["key_nullability"]["violations"] != []

    def test_analyze_source_batch_ids_in_report(
        self,
        analyzer: SilverDQAnalyzer,
        simple_df: pl.DataFrame,
        mock_config_empty: MagicMock,
    ) -> None:
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        batches = ["batch-001", "batch-002"]
        report = analyzer.analyze(
            data=simple_df,
            run_id="batch-test",
            pipeline="test",
            target_table="silver/test",
            source_batch_ids=batches,
            config=mock_config_empty,
            timestamp=ts,
            primary_keys=[],
        )
        assert report.source_batch_ids == tuple(batches)


# ---------------------------------------------------------------------------
# _distribution_to_dict
# ---------------------------------------------------------------------------


class TestDistributionToDict:
    """Tests for the _distribution_to_dict helper."""

    def test_empty_distribution_serializes(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"id": [1, 2, 3]})
        dist_result = analyzer._statistics.check_value_distribution(df)
        output = analyzer._statistics.distribution_to_dict(dist_result)
        assert "numeric_columns" in output
        assert "categorical_columns" in output
        assert output["status"] == DQCheckStatus.PASS.value

    def test_numeric_distribution_in_dict(self, analyzer: SilverDQAnalyzer) -> None:
        df = pl.DataFrame({"score": [1.0, 2.0, 3.0]})
        dist_result = analyzer._statistics.check_value_distribution(df)
        output = analyzer._statistics.distribution_to_dict(dist_result)
        assert "score" in output["numeric_columns"]
