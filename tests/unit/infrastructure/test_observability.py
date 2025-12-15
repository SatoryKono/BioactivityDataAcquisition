"""Unit tests for observability components."""

from unittest.mock import MagicMock, patch

import pytest
import polars as pl

from bioetl.domain.types import BatchID, RunID, DriftLevel
from bioetl.infrastructure.observability.anomaly import AnomalyDetector
from bioetl.infrastructure.observability.lineage import LineageLogger
from bioetl.infrastructure.observability.metrics import (
    get_circuit_breaker_state_metric,
    get_data_freshness_metric,
    get_dq_validation_score_metric,
    get_provider_health_metric,
)


@pytest.fixture
def mock_prometheus_client():
    """Fixture for a mocked prometheus_client."""
    with patch("prometheus_client.Gauge") as mock_gauge, \
         patch("prometheus_client.Counter") as mock_counter:
        yield mock_gauge, mock_counter


@pytest.fixture
def mock_delta_writer():
    """Fixture for a mocked DeltaWriter."""
    with patch("bioetl.infrastructure.storage.delta_writer.DeltaWriter") as mock_writer:
        yield mock_writer


@pytest.fixture
def mock_delta_table():
    """Fixture for a mocked DeltaTable."""
    with patch("deltalake.DeltaTable") as mock_table:
        yield mock_table


@pytest.mark.unit
class TestMetrics:
    """Test metrics functionality."""

    def test_get_circuit_breaker_state_metric(self, mock_prometheus_client):
        """Test that the circuit breaker state metric is created correctly."""
        mock_gauge, mock_counter = mock_prometheus_client
        get_circuit_breaker_state_metric()
        mock_gauge.assert_called_with(
            "circuit_breaker_state",
            "Circuit breaker state (0=Closed, 1=Half-Open, 2=Open)",
            ["provider"],
        )

    def test_get_data_freshness_metric(self, mock_prometheus_client):
        """Test that the data freshness metric is created correctly."""
        mock_gauge, mock_counter = mock_prometheus_client
        get_data_freshness_metric()
        mock_gauge.assert_called_with(
            "data_freshness_seconds",
            "Data freshness in seconds",
            ["provider", "entity"],
        )

    def test_get_dq_validation_score_metric(self, mock_prometheus_client):
        """Test that the DQ validation score metric is created correctly."""
        mock_gauge, mock_counter = mock_prometheus_client
        get_dq_validation_score_metric()
        mock_gauge.assert_called_with(
            "dq_validation_score",
            "Data quality validation score (0-1)",
            ["check", "column"],
        )

    def test_get_provider_health_metric(self, mock_prometheus_client):
        """Test that the provider health metric is created correctly."""
        mock_gauge, mock_counter = mock_prometheus_client
        get_provider_health_metric()
        mock_gauge.assert_called_with(
            "provider_health_status",
            "Provider health status (0=Unhealthy, 1=Degraded, 2=Healthy)",
            ["provider"],
        )


@pytest.mark.unit
class TestLineageLogger:
    """Test LineageLogger functionality."""

    def test_lineage_logger_initialization(self, mock_delta_writer):
        """Test LineageLogger can be initialized."""
        logger = LineageLogger(delta_writer=mock_delta_writer)
        assert logger.delta_writer is mock_delta_writer

    def test_log_lineage_calls_delta_writer(self, mock_delta_writer):
        """Test that log_lineage calls the underlying DeltaWriter."""
        logger = LineageLogger(delta_writer=mock_delta_writer)
        run_id = RunID.from_hex("12345678123456781234567812345678")
        batch_id = BatchID.from_hex("87654321876543218765432187654321")
        source_uris = ["s3://bucket/key1", "s3://bucket/key2"]

        logger.log_lineage(
            run_id=run_id,
            batch_id=batch_id,
            source_uris=source_uris,
        )

        mock_delta_writer.write_silver.assert_called_once()
        args, kwargs = mock_delta_writer.write_silver.call_args
        assert kwargs["table_name"] == "sys.lineage_log"
        assert isinstance(kwargs["records"], list)
        assert len(kwargs["records"]) == 1
        record = kwargs["records"][0]
        assert record["run_id"] == str(run_id)
        assert record["batch_id"] == str(batch_id)
        assert record["source_uris"] == source_uris


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
        mock_table_instance.to_polars.return_value = pl.DataFrame({
            "null_rate": [0.1, 0.1, 0.1, 0.5],
            "timestamp": [1, 2, 3, 4],
        })
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
        mock_table_instance.to_polars.return_value = pl.DataFrame({
            "record_count": [100, 100, 100, 30],
            "timestamp": [1, 2, 3, 4],
        })
        mock_delta_table.return_value = mock_table_instance

        detector = AnomalyDetector(table_uri="/tmp/test_table")
        level, _ = detector.detect_record_count_anomaly(
            current_record_count=30,
            warn_threshold=0.7,
            critical_threshold=0.5,
        )
        assert level == DriftLevel.CRITICAL
