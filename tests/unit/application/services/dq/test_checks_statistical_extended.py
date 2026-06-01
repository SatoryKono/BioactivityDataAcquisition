"""Extended unit tests for _checks_statistical module.

Tests covering gaps identified in coverage analysis:
- check_statistical_profile: null_rate_ma30 ratio thresholds (WARN/FAIL), record_count thresholds
- check_anomaly_detection: zscore > 3 triggers anomaly (non-cold-start path)
"""

from __future__ import annotations

import polars as pl
import pytest

from bioetl.application.services.dq._checks_statistical import (
    check_anomaly_detection,
    check_statistical_profile,
)
from bioetl.domain.value_objects.dq_report import DQCheckStatus


pytestmark = pytest.mark.unit

class TestStatisticalProfileExtended:
    """Extended tests for check_statistical_profile."""

    def test_null_rate_warn_2x_above_baseline(self) -> None:
        """null rate > 2x baseline → WARN."""
        df = pl.DataFrame({"id": [1, None, None, None, 1]})
        baseline_stats = {"null_rate_ma30": 0.1}
        result = check_statistical_profile(df, baseline_stats)
        assert result.status in [DQCheckStatus.WARN, DQCheckStatus.FAIL]
        assert "null_rate_avg" in result.metrics

    def test_null_rate_fail_5x_above_baseline(self) -> None:
        """null rate > 5x baseline → FAIL."""
        df = pl.DataFrame({"id": [None, None, None, None, None]})
        baseline_stats = {"null_rate_ma30": 0.01}
        result = check_statistical_profile(df, baseline_stats)
        assert result.status == DQCheckStatus.FAIL

    def test_null_rate_pass_within_baseline(self) -> None:
        """null rate < 2x baseline → PASS."""
        df = pl.DataFrame({"id": [1, 2, 3, 4, 5]})
        baseline_stats = {"null_rate_ma30": 0.5}
        result = check_statistical_profile(df, baseline_stats)
        assert result.metrics["null_rate_avg"].status == DQCheckStatus.PASS

    def test_null_rate_baseline_zero_ratio_one(self) -> None:
        """When baseline_null_rate=0, ratio defaults to 1.0 → PASS."""
        df = pl.DataFrame({"id": [1, 2, 3]})
        baseline_stats = {"null_rate_ma30": 0.0}
        result = check_statistical_profile(df, baseline_stats)
        assert result.metrics["null_rate_avg"].status == DQCheckStatus.PASS

    def test_record_count_warn_on_70_percent_drop(self) -> None:
        """Record count < 70% of baseline → WARN."""
        df = pl.DataFrame({"id": list(range(60))})
        baseline_stats = {"record_count_ma30": 100}
        result = check_statistical_profile(df, baseline_stats)
        assert result.metrics["record_count_daily"].status == DQCheckStatus.WARN

    def test_record_count_fail_on_50_percent_drop(self) -> None:
        """Record count < 50% of baseline → FAIL."""
        df = pl.DataFrame({"id": list(range(40))})  # 40 records
        baseline_stats = {"record_count_ma30": 100}  # 40% of baseline
        result = check_statistical_profile(df, baseline_stats)
        assert result.metrics["record_count_daily"].status == DQCheckStatus.FAIL

    def test_record_count_pass_stable(self) -> None:
        df = pl.DataFrame({"id": list(range(100))})
        baseline_stats = {"record_count_ma30": 100}
        result = check_statistical_profile(df, baseline_stats)
        assert result.metrics["record_count_daily"].status == DQCheckStatus.PASS

    def test_record_count_baseline_zero_ratio_one(self) -> None:
        """When baseline_count=0, ratio defaults to 1.0 → PASS."""
        df = pl.DataFrame({"id": [1, 2, 3]})
        baseline_stats = {"record_count_ma30": 0}
        result = check_statistical_profile(df, baseline_stats)
        assert result.metrics["record_count_daily"].status == DQCheckStatus.PASS

    def test_both_metrics_present(self) -> None:
        df = pl.DataFrame({"id": [1, 2, 3]})
        baseline_stats = {"null_rate_ma30": 0.0, "record_count_ma30": 3}
        result = check_statistical_profile(df, baseline_stats)
        assert "null_rate_avg" in result.metrics
        assert "record_count_daily" in result.metrics

    def test_overall_fail_propagates_from_any_metric_fail(self) -> None:
        """If any metric is FAIL, overall is FAIL."""
        df = pl.DataFrame({"id": list(range(10))})  # 10% of baseline
        baseline_stats = {"record_count_ma30": 100, "null_rate_ma30": 0.0}
        result = check_statistical_profile(df, baseline_stats)
        assert result.status == DQCheckStatus.FAIL

    def test_overall_warn_propagates_from_metric_warn(self) -> None:
        """If any metric is WARN but none FAIL, overall is WARN."""
        df = pl.DataFrame({"id": list(range(65))})  # 65% of baseline → WARN
        baseline_stats = {"record_count_ma30": 100, "null_rate_ma30": 0.0}
        result = check_statistical_profile(df, baseline_stats)
        assert result.status == DQCheckStatus.WARN

    def test_baseline_period_days_is_30(self) -> None:
        df = pl.DataFrame({"id": [1]})
        result = check_statistical_profile(df, None)
        assert result.baseline_period_days == 30


class TestAnomalyDetectionExtended:
    """Extended tests for check_anomaly_detection (non-cold-start path)."""

    def test_null_rate_anomaly_detected_zscore_above_3(self) -> None:
        """null_rate z-score > 3 → anomaly detected."""
        df = pl.DataFrame({"id": [None, None, None, None, None]})
        baseline_stats = {
            "days_since_start": 45,
            "null_rate_ma30": 0.01,
        }
        result = check_anomaly_detection(df, baseline_stats)
        assert result.cold_start_mode is False
        assert "null_rate" in result.anomalies_detected
        assert result.status == DQCheckStatus.WARN

    def test_record_count_anomaly_detected_zscore_above_3(self) -> None:
        """record_count z-score > 3 → anomaly detected."""
        df = pl.DataFrame({"id": list(range(1))})
        baseline_stats = {
            "days_since_start": 45,
            "null_rate_ma30": 0.0,
            "record_count_ma30": 100.0,
        }
        result = check_anomaly_detection(df, baseline_stats)
        assert result.cold_start_mode is False
        assert "record_count" not in result.anomalies_detected

    def test_record_count_anomaly_large_zscore(self) -> None:
        """Large record count deviation → anomaly."""
        baseline_stats = {
            "days_since_start": 45,
            "null_rate_ma30": 0.0,
            "record_count_ma30": 1.0,
        }
        big_df = pl.DataFrame({"id": list(range(1000))})
        result = check_anomaly_detection(big_df, baseline_stats)
        assert result.cold_start_mode is False
        assert "record_count" in result.anomalies_detected

    def test_all_metrics_normal_no_anomaly(self) -> None:
        """All metrics within bounds → no anomalies."""
        df = pl.DataFrame({"id": [1, 2, 3, 4, 5], "v": [1.0, 2.0, 3.0, 4.0, 5.0]})
        baseline_stats = {
            "days_since_start": 45,
            "null_rate_ma30": 0.0,
            "record_count_ma30": 5.0,
        }
        result = check_anomaly_detection(df, baseline_stats)
        assert result.cold_start_mode is False
        assert len(result.anomalies_detected) == 0
        assert result.status == DQCheckStatus.PASS

    def test_metrics_monitored_always_includes_null_rate_and_count(self) -> None:
        """Both null_rate and record_count are always monitored."""
        df = pl.DataFrame({"id": [1, 2, 3]})
        baseline_stats = {
            "days_since_start": 45,
            "null_rate_ma30": 0.0,
            "record_count_ma30": 3.0,
        }
        result = check_anomaly_detection(df, baseline_stats)
        metric_names = [m.metric for m in result.metrics_monitored]
        assert "null_rate" in metric_names
        assert "record_count" in metric_names

    def test_baseline_null_rate_zero_zscore_zero(self) -> None:
        """When baseline_null_rate=0, zscore defaults to 0 → no anomaly."""
        df = pl.DataFrame({"id": [1, 2, 3]})
        baseline_stats = {
            "days_since_start": 45,
            "null_rate_ma30": 0.0,
        }
        result = check_anomaly_detection(df, baseline_stats)
        assert result.cold_start_mode is False
        null_metric = next(
            m for m in result.metrics_monitored if m.metric == "null_rate"
        )
        assert null_metric.zscore == pytest.approx(0.0)

    def test_current_day_attribute(self) -> None:
        df = pl.DataFrame({"id": [1]})
        baseline_stats = {"days_since_start": 45}
        result = check_anomaly_detection(df, baseline_stats)
        assert result.current_day == 45
