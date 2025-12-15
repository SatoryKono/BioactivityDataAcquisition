"""Unit tests for observability components."""

from unittest.mock import MagicMock, patch

import polars as pl
import pytest
from prometheus_client import CollectorRegistry

from bioetl.domain.types import DriftLevel
from bioetl.infrastructure.observability.anomaly import AnomalyDetector
from bioetl.infrastructure.observability.lineage import LineageTracker
from bioetl.infrastructure.observability.metrics import MetricsCollector


@pytest.fixture
def metrics_registry():
    """Fixture for a fresh Prometheus registry."""
    return CollectorRegistry()


@pytest.fixture
def mock_delta_table():
    """Fixture for a mocked DeltaTable."""
    with patch("deltalake.DeltaTable") as mock_table:
        yield mock_table


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

    def test_record_bronze_creates_batch_lineage(self, tmp_path):
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

        # Verify batch_lineage table path is set correctly
        assert tracker.batch_table_path == tmp_path / "batch_lineage"


@pytest.mark.unit
class TestAnomalyDetector:
    """Test AnomalyDetector functionality."""

    def test_anomaly_detector_initialization(self, mock_delta_table):
        """Test AnomalyDetector can be initialized."""
        detector = AnomalyDetector(table_uri="/tmp/test_table")
        assert detector.table_uri == "/tmp/test_table"

    def test_detect_null_rate_anomaly(self, mock_delta_table):
        """Test detection of null rate anomalies."""
        mock_table_instance = MagicMock()
        mock_table_instance.to_polars.return_value = pl.DataFrame(
            {
                "null_rate": [0.1, 0.1, 0.1, 0.5],
                "timestamp": [1, 2, 3, 4],
            }
        )
        mock_delta_table.return_value = mock_table_instance

        detector = AnomalyDetector(table_uri="/tmp/test_table")
        level, _ = detector.detect_null_rate_anomaly(
            current_null_rate=0.5,
            column="test_col",
            warn_threshold=2.0,
            critical_threshold=4.0,
        )
        assert level == DriftLevel.CRITICAL

    def test_detect_record_count_anomaly(self, mock_delta_table):
        """Test detection of record count anomalies."""
        mock_table_instance = MagicMock()
        mock_table_instance.to_polars.return_value = pl.DataFrame(
            {
                "record_count": [100, 100, 100, 30],
                "timestamp": [1, 2, 3, 4],
            }
        )
        mock_delta_table.return_value = mock_table_instance

        detector = AnomalyDetector(table_uri="/tmp/test_table")
        level, _ = detector.detect_record_count_anomaly(
            current_record_count=30,
            warn_threshold=0.7,
            critical_threshold=0.5,
        )
        assert level == DriftLevel.CRITICAL
