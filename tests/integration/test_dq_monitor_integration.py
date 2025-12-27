"""Integration tests for Data Quality Monitor.

Tests the full DQ monitor flow including anomaly detection,
baseline updates, and threshold violations.
"""

from __future__ import annotations

from datetime import datetime, UTC

import pytest

from bioetl.infrastructure.observability.anomaly import DataQualityMonitor
from bioetl.infrastructure.observability.anomaly.types import (
    AnomalySeverity,
    AnomalyType,
)


@pytest.mark.integration
class TestDQMonitorAnomalyDetection:
    """Integration tests for anomaly detection."""

    def test_dq_monitor_detects_spike(self) -> None:
        """DQ Monitor should detect record count spike."""
        monitor = DataQualityMonitor(z_score_threshold=2.0)

        # Build baseline with normal values
        for _ in range(5):
            monitor.update_baseline_from_metrics({"record_count": 1000.0})

        # Check with spike
        anomalies = monitor.check_quality(
            {"record_count": 5000.0}, timestamp=datetime.now(UTC)
        )

        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == AnomalyType.SPIKE
        assert anomalies[0].severity in (AnomalySeverity.HIGH, AnomalySeverity.CRITICAL)

    def test_dq_monitor_detects_drop(self) -> None:
        """DQ Monitor should detect record count drop."""
        monitor = DataQualityMonitor(z_score_threshold=2.0)

        # Build baseline with slight variation (required for stddev > 0)
        for value in [980.0, 1000.0, 1020.0, 990.0, 1010.0]:
            monitor.update_baseline_from_metrics({"record_count": value})

        # Check with significant drop (z-score will be high)
        anomalies = monitor.check_quality(
            {"record_count": 100.0}, timestamp=datetime.now(UTC)
        )

        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == AnomalyType.DROP

    def test_dq_monitor_threshold_exceeded(self) -> None:
        """DQ Monitor should detect threshold violations."""
        monitor = DataQualityMonitor()
        monitor.detector.set_threshold("error_rate", min_value=0.0, max_value=0.10)

        anomalies = monitor.check_quality(
            {"error_rate": 0.25}, timestamp=datetime.now(UTC)
        )

        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == AnomalyType.THRESHOLD_EXCEEDED
        assert anomalies[0].severity == AnomalySeverity.CRITICAL

    def test_dq_monitor_no_anomalies_within_range(self) -> None:
        """DQ Monitor should not detect anomalies for normal values."""
        monitor = DataQualityMonitor(z_score_threshold=2.0)

        # Build baseline
        for _ in range(5):
            monitor.update_baseline_from_metrics({"record_count": 1000.0})

        # Check with value close to baseline
        anomalies = monitor.check_quality(
            {"record_count": 1050.0}, timestamp=datetime.now(UTC)
        )

        assert len(anomalies) == 0

    def test_dq_monitor_updates_baseline(self) -> None:
        """DQ Monitor should update baseline with new metrics."""
        monitor = DataQualityMonitor()

        # Initial update
        monitor.update_baseline_from_metrics({"record_count": 1000.0})
        stats = monitor.get_baseline_stats("record_count")

        assert stats is not None
        mean, _stddev, count = stats
        assert count == 1
        assert mean == 1000.0

        # Second update
        monitor.update_baseline_from_metrics({"record_count": 2000.0})
        stats = monitor.get_baseline_stats("record_count")

        assert stats is not None
        mean, _stddev, count = stats
        assert count == 2
        assert mean == 1500.0  # Average of 1000 and 2000


@pytest.mark.integration
class TestDQMonitorSeverityLevels:
    """Tests for severity level determination."""

    def test_low_severity_for_small_deviation(self) -> None:
        """Small deviations should get LOW severity."""
        monitor = DataQualityMonitor(z_score_threshold=2.0)

        # Build baseline with consistent values
        # mean=100, stddev≈1.58
        for value in [100.0, 102.0, 98.0, 101.0, 99.0]:
            monitor.detector.add_baseline_value("metric", value)

        # Value that gives z-score ~2.5 (between 2.0 and 3.0 for LOW severity)
        # z = |104 - 100| / 1.58 ≈ 2.53
        anomalies = monitor.check_quality(
            {"metric": 104.0}, timestamp=datetime.now(UTC)
        )

        assert len(anomalies) == 1
        assert anomalies[0].severity == AnomalySeverity.LOW

    def test_critical_severity_for_extreme_deviation(self) -> None:
        """Extreme deviations should get CRITICAL severity."""
        monitor = DataQualityMonitor(z_score_threshold=2.0)

        # Build baseline with consistent values
        for value in [100.0, 102.0, 98.0, 101.0, 99.0]:
            monitor.detector.add_baseline_value("metric", value)

        # Extreme value (z-score > 5)
        anomalies = monitor.check_quality(
            {"metric": 200.0}, timestamp=datetime.now(UTC)
        )

        assert len(anomalies) == 1
        assert anomalies[0].severity == AnomalySeverity.CRITICAL


@pytest.mark.integration
class TestDQMonitorBaselineManagement:
    """Tests for baseline management behavior."""

    def test_baseline_not_updated_on_critical_anomaly(self) -> None:
        """Baseline should not be updated when critical anomaly detected."""
        monitor = DataQualityMonitor(z_score_threshold=2.0)
        monitor.detector.set_threshold("error_rate", min_value=0.0, max_value=0.10)

        # Add initial baseline
        monitor.detector.add_baseline_value("error_rate", 0.05)
        monitor.detector.add_baseline_value("error_rate", 0.04)
        monitor.detector.add_baseline_value("error_rate", 0.06)

        initial_stats = monitor.get_baseline_stats("error_rate")
        initial_count = initial_stats[2] if initial_stats else 0

        # Update with critical violation
        monitor.update_baseline_from_metrics(
            {"error_rate": 0.50}, timestamp=datetime.now(UTC)
        )

        # Baseline should not be updated
        final_stats = monitor.get_baseline_stats("error_rate")
        final_count = final_stats[2] if final_stats else 0

        assert final_count == initial_count

    def test_baseline_window_limits_samples(self) -> None:
        """Baseline should respect window size limit."""
        monitor = DataQualityMonitor(baseline_window=5)

        # Add more samples than window size
        for i in range(10):
            monitor.detector.add_baseline_value("metric", float(i * 100))

        stats = monitor.get_baseline_stats("metric")
        assert stats is not None
        _, _, count = stats
        assert count == 5  # Only last 5 values kept
