"""Unit tests for IQR and MAD anomaly detectors."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.infrastructure.observability.anomaly.detectors.iqr import IQRDetector
from bioetl.infrastructure.observability.anomaly.detectors.mad import MADDetector
from bioetl.infrastructure.observability.anomaly.types import (
    AnomalySeverity,
    AnomalyType,
)


@pytest.mark.unit
class TestIQRDetector:
    """Tests for IQRDetector class."""

    @pytest.fixture
    def detector(self):
        """Create an IQR detector instance."""
        return IQRDetector()

    def test_detect_returns_none_for_insufficient_samples(self, detector):
        """Test that detect returns None when baseline has < 4 samples."""
        baseline = [100.0, 110.0, 120.0]  # Only 3 samples
        result = detector.detect("metric", 500.0, baseline, timestamp=datetime.now(UTC))
        assert result is None

    def test_detect_returns_none_for_zero_iqr(self, detector):
        """Test that detect returns None when IQR is zero."""
        baseline = [100.0, 100.0, 100.0, 100.0, 100.0]  # All same values
        result = detector.detect("metric", 500.0, baseline, timestamp=datetime.now(UTC))
        assert result is None

    def test_detect_returns_none_for_normal_value(self, detector):
        """Test that detect returns None for value within bounds."""
        baseline = [100.0, 110.0, 120.0, 130.0, 140.0]
        result = detector.detect(
            "metric", 125.0, baseline, timestamp=datetime.now(UTC)
        )  # Within IQR
        assert result is None

    def test_detect_spike_anomaly(self, detector):
        """Test detection of spike (value above Q3)."""
        baseline = [100.0, 110.0, 120.0, 130.0, 140.0]
        result = detector.detect(
            "metric", 200.0, baseline, threshold=1.0, timestamp=datetime.now(UTC)
        )

        assert result is not None
        assert result.anomaly_type == AnomalyType.SPIKE
        assert result.current_value == 200.0
        assert "IQR" in result.message

    def test_detect_drop_anomaly(self, detector):
        """Test detection of drop (value below Q1)."""
        baseline = [100.0, 110.0, 120.0, 130.0, 140.0]
        result = detector.detect(
            "metric", 50.0, baseline, threshold=1.0, timestamp=datetime.now(UTC)
        )

        assert result is not None
        assert result.anomaly_type == AnomalyType.DROP
        assert result.current_value == 50.0

    def test_calculate_quartiles(self, detector):
        """Test quartile calculation."""
        data = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0]
        q1, q3 = detector._calculate_quartiles(data)

        # n=8, q1_idx = 8 // 4 = 2, q3_idx = (3 * 8) // 4 = 6
        assert q1 == 30.0  # sorted_data[2] = 30.0
        assert q3 == 70.0  # sorted_data[6] = 70.0

    def test_calculate_iqr_score_below_q1(self, detector):
        """Test IQR score for value below Q1."""
        score = detector._calculate_iqr_score(50.0, q1=100.0, q3=200.0, iqr=100.0)
        assert score == 0.5  # (100 - 50) / 100 = 0.5

    def test_calculate_iqr_score_above_q3(self, detector):
        """Test IQR score for value above Q3."""
        score = detector._calculate_iqr_score(250.0, q1=100.0, q3=200.0, iqr=100.0)
        assert score == 0.5  # (250 - 200) / 100 = 0.5

    def test_calculate_iqr_score_within_bounds(self, detector):
        """Test IQR score for value within Q1-Q3."""
        score = detector._calculate_iqr_score(150.0, q1=100.0, q3=200.0, iqr=100.0)
        assert score == 0.0

    def test_get_severity_critical(self, detector):
        """Test critical severity for score >= 5.0."""
        severity = detector.get_severity(5.5)
        assert severity == AnomalySeverity.CRITICAL

    def test_get_severity_high(self, detector):
        """Test high severity for score >= 3.5."""
        severity = detector.get_severity(4.0)
        assert severity == AnomalySeverity.HIGH

    def test_get_severity_medium(self, detector):
        """Test medium severity for score >= 2.5."""
        severity = detector.get_severity(3.0)
        assert severity == AnomalySeverity.MEDIUM

    def test_get_severity_low(self, detector):
        """Test low severity for score < 2.5."""
        severity = detector.get_severity(2.0)
        assert severity == AnomalySeverity.LOW

    def test_create_anomaly(self, detector):
        """Test anomaly object creation."""
        ts = datetime.now(UTC)
        anomaly = detector._create_anomaly(
            metric_name="test_metric",
            current_value=300.0,
            mean=100.0,
            stddev=20.0,
            score=4.0,
            timestamp=ts,
        )

        assert anomaly.metric_name == "test_metric"
        assert anomaly.current_value == 300.0
        assert anomaly.baseline_mean == 100.0
        assert anomaly.baseline_stddev == 20.0
        assert anomaly.z_score == 4.0
        assert anomaly.severity == AnomalySeverity.HIGH
        assert anomaly.anomaly_type == AnomalyType.SPIKE
        assert anomaly.timestamp == ts

    def test_create_anomaly_drop_type(self, detector):
        """Test anomaly type is DROP when value is below mean."""
        anomaly = detector._create_anomaly(
            metric_name="test_metric",
            current_value=50.0,
            mean=100.0,
            stddev=20.0,
            score=3.0,
            timestamp=datetime.now(UTC),
        )

        assert anomaly.anomaly_type == AnomalyType.DROP

    def test_min_samples_constant(self, detector):
        """Test MIN_SAMPLES constant is 4."""
        assert detector.MIN_SAMPLES == 4


@pytest.mark.unit
class TestMADDetector:
    """Tests for MADDetector class."""

    @pytest.fixture
    def detector(self):
        """Create a MAD detector instance."""
        return MADDetector()

    def test_detect_returns_none_for_insufficient_samples(self, detector):
        """Test that detect returns None when baseline has < 3 samples."""
        baseline = [100.0, 110.0]  # Only 2 samples
        result = detector.detect("metric", 500.0, baseline, timestamp=datetime.now(UTC))
        assert result is None

    def test_detect_returns_none_for_zero_mad(self, detector):
        """Test that detect returns None when MAD is zero."""
        baseline = [100.0, 100.0, 100.0, 100.0]  # All same values
        result = detector.detect("metric", 500.0, baseline, timestamp=datetime.now(UTC))
        assert result is None

    def test_detect_returns_none_for_normal_value(self, detector):
        """Test that detect returns None for value within threshold."""
        baseline = [100.0, 110.0, 120.0, 130.0, 140.0]
        result = detector.detect(
            "metric", 120.0, baseline, timestamp=datetime.now(UTC)
        )  # Close to median
        assert result is None

    def test_detect_spike_anomaly(self, detector):
        """Test detection of spike (high value)."""
        baseline = [100.0, 110.0, 120.0, 130.0, 140.0]
        result = detector.detect(
            "metric", 300.0, baseline, threshold=1.0, timestamp=datetime.now(UTC)
        )

        assert result is not None
        assert result.anomaly_type == AnomalyType.SPIKE
        assert result.current_value == 300.0
        assert "modified Z-score" in result.message

    def test_detect_drop_anomaly(self, detector):
        """Test detection of drop (low value)."""
        baseline = [100.0, 110.0, 120.0, 130.0, 140.0]
        result = detector.detect(
            "metric", 10.0, baseline, threshold=1.0, timestamp=datetime.now(UTC)
        )

        assert result is not None
        assert result.anomaly_type == AnomalyType.DROP
        assert result.current_value == 10.0

    def test_calculate_mad(self, detector):
        """Test MAD calculation."""
        data = [10.0, 20.0, 30.0, 40.0, 50.0]
        median = 30.0
        mad = detector._calculate_mad(data, median)

        # Deviations: [20, 10, 0, 10, 20] -> median = 10
        # MAD = 10 * 1.4826 = 14.826
        assert abs(mad - 14.826) < 0.01

    def test_calculate_modified_zscore(self, detector):
        """Test modified Z-score calculation."""
        score = detector._calculate_modified_zscore(150.0, median=100.0, mad=25.0)
        assert score == 2.0  # abs(150 - 100) / 25 = 2.0

    def test_get_severity_critical(self, detector):
        """Test critical severity for score >= 5.0."""
        severity = detector.get_severity(5.5)
        assert severity == AnomalySeverity.CRITICAL

    def test_get_severity_high(self, detector):
        """Test high severity for score >= 4.0."""
        severity = detector.get_severity(4.5)
        assert severity == AnomalySeverity.HIGH

    def test_get_severity_medium(self, detector):
        """Test medium severity for score >= 3.0."""
        severity = detector.get_severity(3.5)
        assert severity == AnomalySeverity.MEDIUM

    def test_get_severity_low(self, detector):
        """Test low severity for score < 3.0."""
        severity = detector.get_severity(2.5)
        assert severity == AnomalySeverity.LOW

    def test_create_anomaly(self, detector):
        """Test anomaly object creation."""
        ts = datetime.now(UTC)
        anomaly = detector._create_anomaly(
            metric_name="test_metric",
            current_value=300.0,
            mean=100.0,
            stddev=20.0,
            score=4.5,
            timestamp=ts,
        )

        assert anomaly.metric_name == "test_metric"
        assert anomaly.current_value == 300.0
        assert anomaly.baseline_mean == 100.0
        assert anomaly.baseline_stddev == 20.0
        assert anomaly.z_score == 4.5
        assert anomaly.severity == AnomalySeverity.HIGH
        assert anomaly.anomaly_type == AnomalyType.SPIKE
        assert anomaly.timestamp == ts

    def test_create_anomaly_drop_type(self, detector):
        """Test anomaly type is DROP when value is below mean."""
        anomaly = detector._create_anomaly(
            metric_name="test_metric",
            current_value=50.0,
            mean=100.0,
            stddev=20.0,
            score=3.5,
            timestamp=datetime.now(UTC),
        )

        assert anomaly.anomaly_type == AnomalyType.DROP

    def test_min_samples_constant(self, detector):
        """Test MIN_SAMPLES constant is 3."""
        assert detector.MIN_SAMPLES == 3

    def test_consistency_constant(self, detector):
        """Test CONSISTENCY_CONSTANT is set correctly."""
        assert abs(detector.CONSISTENCY_CONSTANT - 1.4826) < 0.0001


@pytest.mark.unit
class TestDetectorEdgeCases:
    """Edge case tests for both detectors."""

    def test_iqr_with_negative_values(self):
        """Test IQR detector with negative values."""
        detector = IQRDetector()
        baseline = [-100.0, -90.0, -80.0, -70.0, -60.0]
        result = detector.detect(
            "metric", -200.0, baseline, threshold=1.0, timestamp=datetime.now(UTC)
        )

        assert result is not None
        assert result.anomaly_type == AnomalyType.DROP

    def test_mad_with_negative_values(self):
        """Test MAD detector with negative values."""
        detector = MADDetector()
        baseline = [-100.0, -90.0, -80.0, -70.0, -60.0]
        result = detector.detect(
            "metric", -200.0, baseline, threshold=1.0, timestamp=datetime.now(UTC)
        )

        assert result is not None
        assert result.anomaly_type == AnomalyType.DROP

    def test_iqr_with_large_baseline(self):
        """Test IQR detector with large baseline."""
        detector = IQRDetector()
        baseline = list(range(1, 101))  # 1 to 100
        result = detector.detect(
            "metric", 200.0, baseline, threshold=1.0, timestamp=datetime.now(UTC)
        )

        assert result is not None

    def test_mad_with_large_baseline(self):
        """Test MAD detector with large baseline."""
        detector = MADDetector()
        baseline = list(range(1, 101))  # 1 to 100
        result = detector.detect(
            "metric", 200.0, baseline, threshold=1.0, timestamp=datetime.now(UTC)
        )

        assert result is not None

    def test_iqr_exact_threshold(self):
        """Test IQR detector at exact threshold boundary."""
        detector = IQRDetector()
        baseline = [100.0, 110.0, 120.0, 130.0, 140.0]
        # Test with threshold of 1.5 (default)
        result = detector.detect(
            "metric", 175.0, baseline, threshold=1.5, timestamp=datetime.now(UTC)
        )

        # Value should be just at or past threshold
        if result is not None:
            assert result.z_score >= 1.5

    def test_mad_exact_threshold(self):
        """Test MAD detector at exact threshold boundary."""
        detector = MADDetector()
        baseline = [100.0, 110.0, 120.0, 130.0, 140.0]
        # Test with threshold of 2.0 (default)
        result = detector.detect(
            "metric", 120.0, baseline, threshold=2.0, timestamp=datetime.now(UTC)
        )

        # Should be None since value is close to median
        assert result is None
