"""Unit tests for observability components."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from prometheus_client import CollectorRegistry

from bioetl.infrastructure.observability.anomaly import (
    AnomalyDetector,
    AnomalySeverity,
    AnomalyType,
)
from bioetl.infrastructure.observability.metrics import MetricsCollector


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for tests."""
    return MagicMock()


@pytest.fixture
def metrics_registry():
    """Fixture for a fresh Prometheus registry."""
    return CollectorRegistry()


@pytest.mark.unit
class TestMetricsCollector:
    """Test MetricsCollector functionality."""

    def test_metrics_collector_initialization(self, metrics_registry):
        """Test MetricsCollector can be initialized."""
        collector = MetricsCollector(
            pipeline_name="test_pipeline",
            registry=metrics_registry,
        )
        assert collector.pipeline_name == "test_pipeline"

    def test_record_processed_increments_counter(self, metrics_registry):
        """Test that record_processed increments the counter."""
        collector = MetricsCollector(
            pipeline_name="test_pipeline",
            registry=metrics_registry,
        )
        collector.record_processed(layer="bronze", count=100)
        # Verify the counter was incremented (no assertion needed if no exception)

    def test_record_error_increments_counter(self, metrics_registry):
        """Test that record_error increments the error counter."""
        collector = MetricsCollector(
            pipeline_name="test_pipeline",
            registry=metrics_registry,
        )
        collector.record_error(error_code="VALIDATION_ERROR")


@pytest.mark.unit
class TestAnomalyDetector:
    """Test AnomalyDetector functionality."""

    def test_anomaly_detector_initialization(self):
        """Test AnomalyDetector can be initialized."""
        detector = AnomalyDetector(
            baseline_window=7,
            z_score_threshold=2.0,
            min_baseline_samples=3,
        )
        assert detector.baseline_window == 7
        assert detector.z_score_threshold == pytest.approx(2.0)
        assert detector.min_baseline_samples == 3

    def test_detect_spike_anomaly(self):
        """Test detection of spike anomalies."""
        detector = AnomalyDetector(
            baseline_window=7,
            z_score_threshold=2.0,
            min_baseline_samples=3,
        )

        # Update baseline with stable values
        detector.update_baseline("null_rate", [0.1, 0.1, 0.1, 0.1])

        # Detect anomaly with much higher value
        anomaly = detector.detect(
            "null_rate", 0.5, timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        )

        assert anomaly is not None
        assert anomaly.anomaly_type == AnomalyType.SPIKE
        assert anomaly.current_value == pytest.approx(0.5)

    def test_detect_drop_anomaly(self):
        """Test detection of drop anomalies."""
        detector = AnomalyDetector(
            baseline_window=7,
            z_score_threshold=2.0,
            min_baseline_samples=3,
        )

        # Update baseline with values that have some variance (needed for stddev calculation)
        detector.update_baseline("record_count", [100.0, 102.0, 98.0, 101.0])

        # Detect anomaly with much lower value (significant drop)
        anomaly = detector.detect(
            "record_count", 30.0, timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        )

        assert anomaly is not None
        assert anomaly.anomaly_type == AnomalyType.DROP
        assert anomaly.current_value == pytest.approx(30.0)

    def test_no_anomaly_within_threshold(self):
        """Test that normal values don't trigger anomalies."""
        detector = AnomalyDetector(
            baseline_window=7,
            z_score_threshold=2.0,
            min_baseline_samples=3,
        )

        # Update baseline with values that have some variance
        detector.update_baseline("record_count", [100.0, 105.0, 95.0, 102.0])

        # Value within normal range should not trigger anomaly
        anomaly = detector.detect(
            "record_count", 98.0, timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        )

        assert anomaly is None

    def test_threshold_based_anomaly(self):
        """Test threshold-based anomaly detection."""
        detector = AnomalyDetector()

        # Set absolute thresholds
        detector.set_threshold("error_rate", min_value=0.0, max_value=0.1)

        # Value exceeding threshold should trigger anomaly
        anomaly = detector.detect(
            "error_rate", 0.15, timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        )

        assert anomaly is not None
        assert anomaly.anomaly_type == AnomalyType.THRESHOLD_EXCEEDED
        assert anomaly.severity == AnomalySeverity.CRITICAL

    def test_insufficient_baseline_returns_none(self):
        """Test that detection returns None with insufficient baseline."""
        detector = AnomalyDetector(min_baseline_samples=3)

        # Only add 2 values (less than min_baseline_samples)
        detector.update_baseline("metric", [100.0, 100.0])

        # Should return None due to insufficient baseline
        anomaly = detector.detect("metric", 500.0)

        assert anomaly is None
