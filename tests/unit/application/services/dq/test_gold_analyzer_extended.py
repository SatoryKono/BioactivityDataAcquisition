"""Extended unit tests for GoldDQAnalyzer _execute_checks branches.

Tests covering gaps in gold_analyzer.py:
- REFERENTIAL_INTEGRITY check type delegation
- STATISTICAL_PROFILE check type delegation
- ANOMALY_DETECTION check type delegation
- SCD_INTEGRITY check type delegation
- All checks enabled together (integration path)
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.services.dq.gold_analyzer import GoldDQAnalyzer
from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    GoldDQCheckType,
    MedallionLayer,
)


@pytest.fixture()
def analyzer() -> GoldDQAnalyzer:
    return GoldDQAnalyzer()


@pytest.fixture()
def sample_df() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["a", "b", "c", "d", "e"],
            "value": [100.0, 200.0, 300.0, 400.0, 500.0],
        }
    )


def _make_config(*check_types: GoldDQCheckType) -> MagicMock:
    config = MagicMock()
    config.get_checks_enums.return_value = list(check_types)
    return config


class TestGoldAnalyzerReferentialIntegrity:
    """Tests that REFERENTIAL_INTEGRITY branch is executed."""

    def test_referential_integrity_check_included(
        self, analyzer: GoldDQAnalyzer, sample_df: pl.DataFrame
    ) -> None:
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        ref_table = pl.DataFrame({"id": [1, 2, 3, 4, 5, 6]})
        config = _make_config(GoldDQCheckType.REFERENTIAL_INTEGRITY)

        report = analyzer.analyze(
            data=sample_df,
            run_id="ri-test",
            pipeline="test",
            target_table="gold/test",
            config=config,
            timestamp=ts,
            reference_tables={"id -> ref_table.id": ref_table},
        )
        assert "referential_integrity" in report.checks
        assert (
            report.checks["referential_integrity"]["status"] == DQCheckStatus.PASS.value
        )

    def test_referential_integrity_with_orphans_warn(
        self, analyzer: GoldDQAnalyzer
    ) -> None:
        """Referential integrity delegates to check_referential_integrity."""
        df = pl.DataFrame({"cat_id": [1, 999, 998, 997]})  # 75% orphans
        ref = pl.DataFrame({"id": [1, 2, 3]})
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        config = _make_config(GoldDQCheckType.REFERENTIAL_INTEGRITY)

        report = analyzer.analyze(
            data=df,
            run_id="ri-fail-test",
            pipeline="test",
            target_table="gold/test",
            config=config,
            timestamp=ts,
            reference_tables={"cat_id -> categories.id": ref},
        )
        assert "referential_integrity" in report.checks
        assert (
            report.checks["referential_integrity"]["status"] == DQCheckStatus.FAIL.value
        )


class TestGoldAnalyzerStatisticalProfile:
    """Tests that STATISTICAL_PROFILE branch is executed."""

    def test_statistical_profile_check_included(
        self, analyzer: GoldDQAnalyzer, sample_df: pl.DataFrame
    ) -> None:
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        config = _make_config(GoldDQCheckType.STATISTICAL_PROFILE)
        baseline_stats = {"null_rate_ma30": 0.0, "record_count_ma30": 5}

        report = analyzer.analyze(
            data=sample_df,
            run_id="sp-test",
            pipeline="test",
            target_table="gold/test",
            config=config,
            timestamp=ts,
            baseline_stats=baseline_stats,
        )
        assert "statistical_profile" in report.checks

    def test_statistical_profile_no_baseline(
        self, analyzer: GoldDQAnalyzer, sample_df: pl.DataFrame
    ) -> None:
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        config = _make_config(GoldDQCheckType.STATISTICAL_PROFILE)

        report = analyzer.analyze(
            data=sample_df,
            run_id="sp-no-baseline",
            pipeline="test",
            target_table="gold/test",
            config=config,
            timestamp=ts,
        )
        assert "statistical_profile" in report.checks
        assert (
            report.checks["statistical_profile"]["status"] == DQCheckStatus.PASS.value
        )


class TestGoldAnalyzerAnomalyDetection:
    """Tests that ANOMALY_DETECTION branch is executed."""

    def test_anomaly_detection_check_included_cold_start(
        self, analyzer: GoldDQAnalyzer, sample_df: pl.DataFrame
    ) -> None:
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        config = _make_config(GoldDQCheckType.ANOMALY_DETECTION)
        baseline_stats = {"days_since_start": 5}  # Cold start

        report = analyzer.analyze(
            data=sample_df,
            run_id="ad-cold-start",
            pipeline="test",
            target_table="gold/test",
            config=config,
            timestamp=ts,
            baseline_stats=baseline_stats,
        )
        assert "anomaly_detection" in report.checks
        assert report.checks["anomaly_detection"]["cold_start_mode"] is True

    def test_anomaly_detection_no_baseline(
        self, analyzer: GoldDQAnalyzer, sample_df: pl.DataFrame
    ) -> None:
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        config = _make_config(GoldDQCheckType.ANOMALY_DETECTION)

        report = analyzer.analyze(
            data=sample_df,
            run_id="ad-no-baseline",
            pipeline="test",
            target_table="gold/test",
            config=config,
            timestamp=ts,
        )
        assert "anomaly_detection" in report.checks


class TestGoldAnalyzerSCDIntegrity:
    """Tests that SCD_INTEGRITY branch is executed."""

    def test_scd_integrity_check_included_no_config(
        self, analyzer: GoldDQAnalyzer, sample_df: pl.DataFrame
    ) -> None:
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        config = _make_config(GoldDQCheckType.SCD_INTEGRITY)

        report = analyzer.analyze(
            data=sample_df,
            run_id="scd-test",
            pipeline="test",
            target_table="gold/test",
            config=config,
            timestamp=ts,
        )
        assert "scd_integrity" in report.checks
        assert report.checks["scd_integrity"]["status"] == DQCheckStatus.PASS.value

    def test_scd_integrity_with_config(self, analyzer: GoldDQAnalyzer) -> None:
        df = pl.DataFrame(
            {
                "entity_id": ["A", "A", "B"],
                "_valid_from": [
                    datetime(2024, 1, 1),
                    datetime(2024, 7, 1),
                    datetime(2024, 1, 1),
                ],
                "_valid_to": [datetime(2024, 6, 30), None, None],
            }
        )
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        config = _make_config(GoldDQCheckType.SCD_INTEGRITY)
        scd_config = {"type": 2, "entity_key": "entity_id"}

        report = analyzer.analyze(
            data=df,
            run_id="scd-with-config",
            pipeline="test",
            target_table="gold/test",
            config=config,
            timestamp=ts,
            scd_config=scd_config,
        )
        assert "scd_integrity" in report.checks
        assert report.checks["scd_integrity"]["total_entities"] == 2


class TestGoldAnalyzerAllChecks:
    """Integration test with all check types enabled."""

    def test_all_checks_enabled(
        self, analyzer: GoldDQAnalyzer, sample_df: pl.DataFrame
    ) -> None:
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        config = _make_config(*list(GoldDQCheckType))
        baseline_stats = {
            "null_rate_ma30": 0.0,
            "record_count_ma30": 5,
            "days_since_start": 5,
        }

        report = analyzer.analyze(
            data=sample_df,
            run_id="all-checks",
            pipeline="test",
            target_table="gold/test",
            config=config,
            timestamp=ts,
            required_fields=["id", "name"],
            baseline_stats=baseline_stats,
        )

        assert report.layer == MedallionLayer.GOLD
        # All 7 check types should be in results
        expected_keys = {
            "record_count",
            "completeness",
            "business_rules",
            "referential_integrity",
            "statistical_profile",
            "anomaly_detection",
            "scd_integrity",
        }
        assert expected_keys.issubset(set(report.checks.keys()))
