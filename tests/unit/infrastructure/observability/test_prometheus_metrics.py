"""Unit tests for PrometheusMetrics."""

from unittest.mock import MagicMock, patch

import pytest

from bioetl.infrastructure.observability.prometheus_metrics import (
    COUNTERS,
    HISTOGRAMS,
    PrometheusMetrics,
)


@pytest.fixture
def prometheus_metrics():
    """Create a PrometheusMetrics instance."""
    return PrometheusMetrics()


@pytest.mark.unit
class TestPrometheusMetrics:
    """Tests for PrometheusMetrics."""

    def test_observe_histogram_valid_metric(self, prometheus_metrics):
        """Test observe_histogram with a valid metric name."""
        with patch.dict(
            HISTOGRAMS,
            {"pipeline_duration_seconds": MagicMock()},
        ):
            prometheus_metrics.observe_histogram(
                name="pipeline_duration_seconds",
                value=123.45,
                labels={"pipeline_name": "test", "status": "success", "run_type": "full"},
            )

            HISTOGRAMS["pipeline_duration_seconds"].labels.assert_called_once_with(
                pipeline_name="test", status="success", run_type="full"
            )
            HISTOGRAMS["pipeline_duration_seconds"].labels().observe.assert_called_once_with(
                123.45
            )

    def test_observe_histogram_unknown_metric(self, prometheus_metrics):
        """Test observe_histogram with unknown metric name does nothing."""
        # Should not raise, just ignore
        prometheus_metrics.observe_histogram(
            name="unknown_metric",
            value=100.0,
            labels={"label": "value"},
        )

    def test_increment_counter_valid_metric(self, prometheus_metrics):
        """Test increment_counter with a valid metric name."""
        with patch.dict(
            COUNTERS,
            {"records_processed_total": MagicMock()},
        ):
            prometheus_metrics.increment_counter(
                name="records_processed_total",
                value=100,
                labels={"pipeline_name": "test", "status": "success"},
            )

            COUNTERS["records_processed_total"].labels.assert_called_once_with(
                pipeline_name="test", status="success"
            )
            COUNTERS["records_processed_total"].labels().inc.assert_called_once_with(100)

    def test_increment_counter_unknown_metric(self, prometheus_metrics):
        """Test increment_counter with unknown metric name does nothing."""
        # Should not raise, just ignore
        prometheus_metrics.increment_counter(
            name="unknown_counter",
            value=50,
            labels={"label": "value"},
        )


@pytest.mark.unit
class TestPrometheusMetricsRegistries:
    """Tests for metric registries."""

    def test_histograms_registry_has_pipeline_duration(self):
        """Test HISTOGRAMS registry contains pipeline_duration_seconds."""
        assert "pipeline_duration_seconds" in HISTOGRAMS

    def test_counters_registry_has_records_processed(self):
        """Test COUNTERS registry contains records_processed_total."""
        assert "records_processed_total" in COUNTERS
