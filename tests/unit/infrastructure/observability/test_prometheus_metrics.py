"""Unit tests for PrometheusMetrics."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.infrastructure.observability.prometheus_metrics import (
    COUNTERS,
    GAUGES,
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
                labels={
                    "pipeline_name": "test",
                    "status": "success",
                    "run_type": "full",
                },
            )

            HISTOGRAMS["pipeline_duration_seconds"].labels.assert_called_once_with(
                pipeline_name="test", status="success", run_type="full"
            )
            HISTOGRAMS[
                "pipeline_duration_seconds"
            ].labels().observe.assert_called_once_with(123.45)

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
            COUNTERS["records_processed_total"].labels().inc.assert_called_once_with(
                100
            )

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


@pytest.mark.unit
class TestPrometheusMetricsGauge:
    """Tests for gauge metrics."""

    def test_set_gauge_valid_metric(self, prometheus_metrics):
        """Test set_gauge with a valid metric name."""
        with patch.dict(
            GAUGES,
            {"circuit_breaker_state": MagicMock()},
        ):
            prometheus_metrics.set_gauge(
                name="circuit_breaker_state",
                value=1.0,
                labels={"adapter": "chembl"},
            )

            GAUGES["circuit_breaker_state"].labels.assert_called_once_with(
                adapter="chembl"
            )
            GAUGES["circuit_breaker_state"].labels().set.assert_called_once_with(1.0)

    def test_set_gauge_unknown_metric(self, prometheus_metrics):
        """Test set_gauge with unknown metric name does nothing."""
        # Should not raise, just ignore
        prometheus_metrics.set_gauge(
            name="unknown_gauge",
            value=42.0,
            labels={"label": "value"},
        )


@pytest.mark.unit
class TestRequiredMetricsSmoke:
    """Smoke tests for required metrics per observability contract.

    REQ-OBS-CONTRACT-001: All metrics defined in docs/contracts/observability.md
    MUST be registered and exportable.
    """

    def test_required_pipeline_metrics_registered(self):
        """Verify all MUST pipeline metrics are in registries."""
        # MUST metrics from docs/contracts/observability.md
        required_histograms = [
            "pipeline_duration_seconds",
            "batch_size_records",
        ]
        required_counters = [
            "records_processed_total",
            "errors_total",
            "dq_records_quarantined_total",
        ]

        for metric in required_histograms:
            assert (
                metric in HISTOGRAMS
            ), f"Required histogram '{metric}' not found in HISTOGRAMS registry"

        for metric in required_counters:
            assert (
                metric in COUNTERS
            ), f"Required counter '{metric}' not found in COUNTERS registry"

    def test_required_circuit_breaker_metrics_registered(self):
        """Verify Circuit Breaker metrics are registered (per ADR-007)."""
        # MUST metrics per ADR-007
        cb_counters = [
            "circuit_breaker_trips_total",
            "circuit_breaker_success_total",
            "circuit_breaker_failure_total",
        ]
        cb_gauges = [
            "circuit_breaker_state",
        ]

        for metric in cb_counters:
            assert (
                metric in COUNTERS
            ), f"Required CB counter '{metric}' not found in COUNTERS registry"

        for metric in cb_gauges:
            assert (
                metric in GAUGES
            ), f"Required CB gauge '{metric}' not found in GAUGES registry"

    def test_metrics_have_correct_labels(self):
        """Verify metrics have expected label names."""
        from bioetl.infrastructure.observability.metrics import (
            CIRCUIT_BREAKER_STATE,
            PIPELINE_DURATION_SECONDS,
        )

        # Pipeline duration should have these labels
        pipeline_labels = PIPELINE_DURATION_SECONDS._labelnames
        assert "pipeline" in pipeline_labels
        assert "stage" in pipeline_labels
        assert "status" in pipeline_labels
        assert "run_type" in pipeline_labels

        # Circuit breaker state should have adapter label
        cb_labels = CIRCUIT_BREAKER_STATE._labelnames
        assert "adapter" in cb_labels


@pytest.mark.unit
class TestPrometheusMetricsClose:
    """Tests for close() method."""

    def test_close_is_idempotent(self, prometheus_metrics):
        """Test that close() can be called multiple times safely."""
        prometheus_metrics.close()
        prometheus_metrics.close()  # Should not raise

        assert prometheus_metrics._closed is True
