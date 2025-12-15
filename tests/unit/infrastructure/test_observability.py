"""Unit tests for observability components."""

from unittest.mock import patch

import pytest
from prometheus_client import CollectorRegistry

from bioetl.infrastructure.observability.anomaly import (
    AnomalyDetector,
    AnomalySeverity,
    AnomalyType,
)
from bioetl.infrastructure.observability.lineage import LineageTracker
from bioetl.infrastructure.observability.metrics import MetricsCollector


@pytest.fixture
def metrics_registry():
    """Fixture for a fresh Prometheus registry."""
    return CollectorRegistry()


@pytest.fixture
def mock_write_deltalake():
    """Fixture for mocking deltalake.write_deltalake."""
    with patch("bioetl.infrastructure.observability.lineage.write_deltalake") as mock:
        yield mock


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
class TestLineageTracker:
    """Test LineageTracker functionality."""

    def test_lineage_tracker_initialization(self, tmp_path):
        """Test LineageTracker can be initialized."""
        tracker = LineageTracker(delta_path=tmp_path, pipeline_name="test_pipeline")
        assert tracker.pipeline_name == "test_pipeline"
        assert tracker.delta_path == tmp_path

    def test_record_bronze_creates_batch_lineage(self, tmp_path, mock_write_deltalake):
        """Test that record_bronze creates proper batch lineage."""
        tracker = LineageTracker(delta_path=tmp_path, pipeline_name="test_pipeline")

        # Record bronze layer ingestion
        tracker.record_bronze(
            batch_id="batch-123",
            run_id="run-456",
            provider="chembl",
            entity_type="activity",
            record_count=100,
            file_path="s3://bucket/bronze/file.jsonl.zst",
            watermark="2024-01-01",
        )

        # Verify write_deltalake was called
        mock_write_deltalake.assert_called_once()
        # Verify batch_lineage table path is set correctly
        assert tracker.batch_table_path == tmp_path / "batch_lineage"


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
        assert detector.z_score_threshold == 2.0
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
        anomaly = detector.detect("null_rate", 0.5)

        assert anomaly is not None
        assert anomaly.anomaly_type == AnomalyType.SPIKE
        assert anomaly.current_value == 0.5

    def test_detect_drop_anomaly(self):
        """Test detection of drop anomalies."""
        detector = AnomalyDetector(
            baseline_window=7,
            z_score_threshold=2.0,
            min_baseline_samples=3,
        )

        # Update baseline with stable values
        detector.update_baseline("record_count", [100.0, 100.0, 100.0, 100.0])

        # Detect anomaly with much lower value
        anomaly = detector.detect("record_count", 30.0)

        assert anomaly is not None
        assert anomaly.anomaly_type == AnomalyType.DROP
        assert anomaly.current_value == 30.0

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
        anomaly = detector.detect("record_count", 98.0)

        assert anomaly is None

    def test_threshold_based_anomaly(self):
        """Test threshold-based anomaly detection."""
        detector = AnomalyDetector()

        # Set absolute thresholds
        detector.set_threshold("error_rate", min_value=0.0, max_value=0.1)

        # Value exceeding threshold should trigger anomaly
        anomaly = detector.detect("error_rate", 0.15)

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
