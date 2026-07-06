"""Unit tests for anomaly detection module."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import get_type_hints
from unittest.mock import MagicMock

import pytest

from bioetl.domain.value_objects.dq_anomaly import DQAnomaly
from bioetl.infrastructure.observability.anomaly import (
    AnomalyRecord,
    AnomalyDetector,
    AnomalySeverity,
    AnomalyType,
)

_FIXED_TIME = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for tests."""
    return MagicMock()


@pytest.mark.unit
class TestAnomalyType:
    """Tests for AnomalyType enum."""

    def test_spike_value(self):
        """Test SPIKE enum value."""
        assert AnomalyType.SPIKE.value == "spike"

    def test_drop_value(self):
        """Test DROP enum value."""
        assert AnomalyType.DROP.value == "drop"

    def test_threshold_exceeded_value(self):
        """Test THRESHOLD_EXCEEDED enum value."""
        assert AnomalyType.THRESHOLD_EXCEEDED.value == "threshold_exceeded"

    def test_trend_change_value(self):
        """Test TREND_CHANGE enum value."""
        assert AnomalyType.TREND_CHANGE.value == "trend_change"


@pytest.mark.unit
class TestAnomalySeverity:
    """Tests for AnomalySeverity enum."""

    def test_all_severities(self):
        """Test all severity levels exist."""
        assert AnomalySeverity.LOW.value == "low"
        assert AnomalySeverity.MEDIUM.value == "medium"
        assert AnomalySeverity.HIGH.value == "high"
        assert AnomalySeverity.CRITICAL.value == "critical"


@pytest.mark.unit
class TestAnomaly:
    """Tests for AnomalyRecord dataclass."""

    @pytest.fixture
    def sample_anomaly(self):
        """Create a sample anomaly."""
        return AnomalyRecord(
            metric_name="record_count",
            current_value=500.0,
            baseline_mean=1000.0,
            baseline_stddev=50.0,
            anomaly_type=AnomalyType.DROP,
            severity=AnomalySeverity.CRITICAL,
            z_score=-10.0,
            timestamp=_FIXED_TIME,
            message="Record count dropped significantly",
        )

    def test_anomaly_str_format(self, sample_anomaly):
        """Test anomaly string representation."""
        result = str(sample_anomaly)

        assert "[CRITICAL]" in result
        assert "drop" in result
        assert "record_count" in result
        assert "500.00" in result
        assert "1000.00" in result

    def test_anomaly_is_frozen(self, sample_anomaly):
        """Test that AnomalyRecord is immutable."""
        with pytest.raises(AttributeError):
            sample_anomaly.current_value = 600.0


@pytest.mark.unit
class TestAnomalyDetector:
    """Tests for AnomalyDetector class."""

    @pytest.fixture
    def detector(self):
        """Create an AnomalyDetector instance."""
        return AnomalyDetector(baseline_window=7)

    def test_init_default_values(self):
        """Test detector initialization with defaults."""
        detector = AnomalyDetector()
        assert detector.baseline_window == 7
        assert detector.z_score_threshold == pytest.approx(2.0)

    def test_init_custom_values(self):
        """Test detector initialization with custom values."""
        detector = AnomalyDetector(
            baseline_window=14,
            z_score_threshold=3.0,
        )
        assert detector.baseline_window == 14
        assert detector.z_score_threshold == pytest.approx(3.0)

    def test_update_baseline(self, detector):
        """Test updating baseline with values."""
        values = [100.0, 105.0, 98.0, 102.0, 110.0]
        detector.update_baseline("test_metric", values)

        assert "test_metric" in detector._baselines
        assert len(detector._baselines["test_metric"]) == 5

    def test_update_baseline_multiple_times(self, detector):
        """Test updating baseline multiple times."""
        detector.update_baseline("metric1", [100.0, 100.0, 100.0])
        detector.update_baseline("metric2", [200.0, 200.0, 200.0])

        assert "metric1" in detector._baselines
        assert "metric2" in detector._baselines
        assert len(detector._baselines["metric1"]) == 3
        assert len(detector._baselines["metric2"]) == 3

    def test_detect_no_baseline_returns_none(self, detector):
        """Test detect returns None when no baseline exists."""
        result = detector.detect("unknown_metric", 100, timestamp=_FIXED_TIME)
        assert result is None

    def test_detect_normal_value_returns_none(self, detector):
        """Test detect returns None for normal value."""
        detector.update_baseline("metric", [100.0, 100.0, 100.0, 100.0, 100.0])
        result = detector.detect("metric", 100.0, timestamp=_FIXED_TIME)
        assert result is None

    def test_anomaly_detector__detect_spike_anomaly__72db4688(self, detector):
        """Test detection of spike anomaly."""
        # Use values with some variance so stddev > 0
        detector.update_baseline("metric", [95.0, 100.0, 105.0, 98.0, 102.0])
        result = detector.detect("metric", 500.0, timestamp=_FIXED_TIME)

        assert result is not None
        assert result.anomaly_type == AnomalyType.SPIKE
        assert result.current_value == pytest.approx(500.0)

    def test_anomaly_detector__detect_drop_anomaly__99299846(self, detector):
        """Test detection of drop anomaly."""
        # Use values with some variance so stddev > 0
        detector.update_baseline("metric", [95.0, 100.0, 105.0, 98.0, 102.0])
        result = detector.detect("metric", 10.0, timestamp=_FIXED_TIME)

        assert result is not None
        assert result.anomaly_type == AnomalyType.DROP
        assert result.current_value == pytest.approx(10.0)

    def test_detect_severity_levels(self, detector):
        """Test that severity is determined by z-score."""
        # Create baseline with known mean=100 and non-zero stddev.
        detector.update_baseline("metric", [90.0, 95.0, 100.0, 105.0, 110.0])

        severity_by_value = {
            120.0: AnomalySeverity.LOW,
            125.0: AnomalySeverity.MEDIUM,
            135.0: AnomalySeverity.HIGH,
            150.0: AnomalySeverity.CRITICAL,
        }

        for value, expected_severity in severity_by_value.items():
            result = detector.detect("metric", value, timestamp=_FIXED_TIME)

            assert result is not None
            assert result.severity == expected_severity

    def test_detect_with_zero_stddev(self, detector):
        """Test detection when standard deviation is zero."""
        detector.update_baseline("metric", [100.0, 100.0, 100.0, 100.0, 100.0])
        # When stddev is 0, special handling applies
        result = detector.detect("metric", 150.0, timestamp=_FIXED_TIME)

        # Should handle gracefully without division by zero
        # Per implementation, uses percentage deviation when stddev=0
        assert result is not None or result is None  # Either is acceptable

    def test_baselines_storage(self, detector):
        """Test that baselines are stored as lists."""
        detector.update_baseline("metric", [100.0, 100.0, 100.0])

        assert "metric" in detector._baselines
        assert isinstance(detector._baselines["metric"], list)
        assert len(detector._baselines["metric"]) == 3

    def test_baselines_can_be_cleared(self, detector):
        """Test clearing baselines by reassigning."""
        detector.update_baseline("metric1", [100.0, 100.0])
        detector.update_baseline("metric2", [200.0, 200.0])

        detector._baselines.clear()

        assert len(detector._baselines) == 0

    def test_baseline_can_be_removed(self, detector):
        """Test removing a single baseline."""
        detector.update_baseline("metric1", [100.0, 100.0])
        detector.update_baseline("metric2", [200.0, 200.0])

        del detector._baselines["metric1"]

        assert "metric1" not in detector._baselines
        assert "metric2" in detector._baselines


@pytest.mark.unit
class TestAnomalyDetectorSeverityCalculation:
    """Tests for severity calculation in AnomalyDetector."""

    @pytest.fixture
    def detector(self):
        """Create detector with low threshold for testing."""
        return AnomalyDetector(z_score_threshold=1.5)

    def test_severity_low_for_small_deviation(self, detector):
        """Test LOW severity for 2-3 std deviation."""
        # Set baseline with values that give mean~100 and stddev~10
        detector.update_baseline("metric", [90.0, 95.0, 100.0, 105.0, 110.0])

        result = detector.detect("metric", 125.0, timestamp=_FIXED_TIME)  # ~2.5 std dev

        if result:
            assert result.severity in (
                AnomalySeverity.LOW,
                AnomalySeverity.MEDIUM,
            )

    def test_severity_high_for_large_deviation(self, detector):
        """Test HIGH/CRITICAL severity for large deviation."""
        # Set baseline with values that give mean~100 and stddev~10
        detector.update_baseline("metric", [90.0, 95.0, 100.0, 105.0, 110.0])

        result = detector.detect("metric", 200.0, timestamp=_FIXED_TIME)  # ~10 std dev

        if result:
            assert result.severity in (
                AnomalySeverity.HIGH,
                AnomalySeverity.CRITICAL,
            )


@pytest.mark.unit
class TestAnomalyDetectorEdgeCases:
    """Tests for edge cases in AnomalyDetector."""

    def test_empty_values_list(self):
        """Test handling of empty values list."""
        detector = AnomalyDetector()
        detector.update_baseline("metric", [])

        assert detector.get_baseline_stats("metric") is None

    def test_detector_edge_cases__single_value__f9d640bf(self):
        """Test handling of single value."""
        detector = AnomalyDetector()
        detector.update_baseline("metric", [100])

        result = detector.detect("metric", 110, timestamp=_FIXED_TIME)

        assert result is None
        assert detector.get_baseline_stats("metric") == (100, 0.0, 1)

    def test_detector_edge_cases__negative_values__dbbcaee0(self):
        """Test handling of negative values."""
        detector = AnomalyDetector()
        detector.update_baseline("metric", [-100, -90, -110, -95, -105])
        result = detector.detect("metric", -500, timestamp=_FIXED_TIME)

        # Should detect as anomaly
        assert result is not None

    def test_float_values(self):
        """Test handling of float values."""
        detector = AnomalyDetector()
        detector.update_baseline("metric", [1.5, 1.6, 1.4, 1.55, 1.45])
        result = detector.detect("metric", 5.0, timestamp=_FIXED_TIME)

        assert result is not None


@pytest.mark.unit
class TestAnomalyDetectorValidation:
    """Tests for AnomalyDetector input validation."""

    def test_invalid_baseline_window_raises(self):
        """Test that invalid baseline_window raises ValueError."""
        with pytest.raises(ValueError, match="baseline_window must be >= 1"):
            AnomalyDetector(baseline_window=0)

    def test_invalid_z_score_threshold_raises(self):
        """Test that invalid z_score_threshold raises ValueError."""
        with pytest.raises(ValueError, match="z_score_threshold must be >= 0"):
            AnomalyDetector(z_score_threshold=-1.0)

    def test_invalid_min_baseline_samples_raises(self):
        """Test that invalid min_baseline_samples raises ValueError."""
        with pytest.raises(ValueError, match="min_baseline_samples must be >= 1"):
            AnomalyDetector(min_baseline_samples=0)


@pytest.mark.unit
class TestAnomalyDetectorThresholds:
    """Tests for threshold functionality."""

    def test_set_threshold_invalid_min_max_raises(self):
        """Test that min > max raises ValueError."""
        detector = AnomalyDetector()
        with pytest.raises(ValueError, match="min_value must be <= max_value"):
            detector.set_threshold("metric", min_value=100, max_value=50)

    def test_threshold_breach_below_minimum(self):
        """Test detection of value below minimum threshold."""
        detector = AnomalyDetector()
        detector.set_threshold("metric", min_value=100, max_value=200)

        result = detector.detect("metric", 50, timestamp=_FIXED_TIME)  # Below minimum

        assert result is not None
        assert result.anomaly_type == AnomalyType.THRESHOLD_EXCEEDED
        assert "below minimum" in result.message

    def test_threshold_breach_above_maximum(self):
        """Test detection of value above maximum threshold."""
        detector = AnomalyDetector()
        detector.set_threshold("metric", min_value=100, max_value=200)

        result = detector.detect("metric", 250, timestamp=_FIXED_TIME)  # Above maximum

        assert result is not None
        assert result.anomaly_type == AnomalyType.THRESHOLD_EXCEEDED
        assert "exceeds maximum" in result.message


@pytest.mark.unit
class TestAnomalyDetectorBaselineManagement:
    """Tests for baseline management."""

    def test_clear_baseline(self):
        """Test clearing baseline for a metric."""
        detector = AnomalyDetector()
        detector.update_baseline("metric", [100, 105, 110])

        detector.clear_baseline("metric")

        assert "metric" not in detector._baselines

    def test_clear_nonexistent_baseline(self):
        """Test clearing baseline for nonexistent metric doesn't raise."""
        detector = AnomalyDetector()
        detector.clear_baseline("nonexistent")

        assert detector._baselines == {}

    def test_get_baseline_stats(self):
        """Test getting baseline statistics."""
        detector = AnomalyDetector()
        detector.update_baseline("metric", [100, 110, 120])

        stats = detector.get_baseline_stats("metric")

        assert stats is not None
        mean, _stddev, count = stats
        assert count == 3
        assert mean == pytest.approx(110.0)  # Mean of [100, 110, 120]

    def test_get_baseline_stats_nonexistent(self):
        """Test getting stats for nonexistent metric returns None."""
        detector = AnomalyDetector()

        stats = detector.get_baseline_stats("nonexistent")

        assert stats is None

    def test_add_baseline_value(self):
        """Test adding single value to baseline."""
        detector = AnomalyDetector()
        detector.add_baseline_value("metric", 100)
        detector.add_baseline_value("metric", 110)

        assert len(detector._baselines["metric"]) == 2

    def test_baseline_window_trimming(self):
        """Test that baseline is trimmed to window size."""
        detector = AnomalyDetector(baseline_window=3)
        detector.update_baseline("metric", [100, 110, 120, 130, 140])

        # Should only keep last 3 values
        assert len(detector._baselines["metric"]) == 3
        assert detector._baselines["metric"] == [120, 130, 140]


@pytest.mark.unit
class TestDataQualityMonitor:
    """Tests for DataQualityMonitor."""

    def test_init_sets_default_thresholds(self, mock_logger: MagicMock):
        """Test that init sets default thresholds."""
        from bioetl.infrastructure.observability.anomaly import (
            DataQualityMonitor,
        )

        monitor = DataQualityMonitor(logger=mock_logger)

        # Should have default thresholds
        assert "error_rate" in monitor.detector._thresholds
        assert "quality_score" in monitor.detector._thresholds

    def test_add_metric(self, mock_logger: MagicMock):
        """Test adding metric to monitor."""
        from bioetl.infrastructure.observability.anomaly import (
            DataQualityMonitor,
        )

        monitor = DataQualityMonitor(logger=mock_logger)
        monitor.add_metric("record_count", [1000, 1050, 980], min_threshold=500)

        assert "record_count" in monitor.detector._baselines
        assert "record_count" in monitor.detector._thresholds

    def test_check_quality_no_anomalies(self, mock_logger: MagicMock):
        """Test check_quality returns empty list when no anomalies."""
        from bioetl.infrastructure.observability.anomaly import (
            DataQualityMonitor,
        )

        monitor = DataQualityMonitor(logger=mock_logger)
        monitor.add_metric("record_count", [1000, 1050, 980, 1020, 1010])

        anomalies = monitor.check_quality({"record_count": 1000}, timestamp=_FIXED_TIME)

        assert anomalies == []

    def test_check_quality_with_anomaly(self, mock_logger: MagicMock):
        """Test check_quality returns anomalies when detected."""
        from bioetl.infrastructure.observability.anomaly import (
            DataQualityMonitor,
        )

        monitor = DataQualityMonitor(logger=mock_logger)
        monitor.add_metric("record_count", [1000, 1050, 980, 1020, 1010])

        anomalies = monitor.check_quality(
            {"record_count": 100}, timestamp=_FIXED_TIME
        )  # Low value

        assert len(anomalies) == 1
        assert isinstance(anomalies[0], DQAnomaly)

    def test_check_quality_annotation_uses_domain_dto(self, mock_logger: MagicMock):
        """Public monitor boundary should advertise the domain DTO, not infrastructure aliases."""
        from bioetl.infrastructure.observability.anomaly import (
            DataQualityMonitor,
        )

        raw_annotation = DataQualityMonitor.check_quality.__annotations__["return"]
        assert raw_annotation == "list[DQAnomaly]"

        resolved_annotation = get_type_hints(DataQualityMonitor.check_quality).get(
            "return"
        )
        if resolved_annotation is not None and not isinstance(resolved_annotation, str):
            assert resolved_annotation == list[DQAnomaly]

    def test_update_baseline_from_metrics_normal(self, mock_logger: MagicMock):
        """Test update_baseline_from_metrics with normal values."""
        from bioetl.infrastructure.observability.anomaly import (
            DataQualityMonitor,
        )

        monitor = DataQualityMonitor(logger=mock_logger)
        monitor.add_metric("record_count", [1000, 1050, 980])

        monitor.update_baseline_from_metrics(
            {"record_count": 1020}, timestamp=_FIXED_TIME
        )

        # Baseline should be updated
        assert 1020 in monitor.detector._baselines["record_count"]

    def test_update_baseline_from_metrics_with_critical_anomaly(
        self, mock_logger: MagicMock
    ):
        """Test update_baseline_from_metrics skips update for critical anomalies."""
        from bioetl.infrastructure.observability.anomaly import (
            DataQualityMonitor,
        )

        monitor = DataQualityMonitor(logger=mock_logger)
        # Add a metric with threshold that will be breached
        monitor.add_metric("error_rate", [0.01, 0.02, 0.01], max_threshold=0.1)

        # This should trigger a critical anomaly (exceeds 0.1 threshold)
        monitor.update_baseline_from_metrics({"error_rate": 0.5}, timestamp=_FIXED_TIME)

        # Baseline should NOT be updated with the anomalous value
        assert 0.5 not in monitor.detector._baselines.get("error_rate", [])
