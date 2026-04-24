"""Explicit MetricsPort contract suite."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.ports import MetricsPort
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.observability.prometheus_metrics import (
    COUNTERS,
    GAUGES,
    HISTOGRAMS,
    PrometheusMetrics,
)


@pytest.mark.unit
class TestMetricsPortContract:
    """Bounded contract assertions for MetricsPort implementations."""

    def test_noop_metrics_implements_metrics_port(self) -> None:
        assert isinstance(NoOpMetrics(warn_on_use=False), MetricsPort)

    def test_prometheus_metrics_implements_metrics_port(self) -> None:
        assert isinstance(PrometheusMetrics(), MetricsPort)

    def test_counter_path_dispatches_bounded_metric_event(self) -> None:
        """One canonical counter path must dispatch to the registered metric."""
        metrics = PrometheusMetrics()

        with patch.dict(COUNTERS, {"bioetl_errors_total": MagicMock()}):
            metrics.increment_counter(
                "bioetl_errors_total",
                1,
                {
                    "pipeline": "chembl_activity",
                    "stage": "silver",
                    "error_code": "schema_violation",
                },
            )

            COUNTERS["bioetl_errors_total"].labels.assert_called_once_with(
                pipeline="chembl_activity",
                stage="silver",
                error_code="schema_violation",
            )
            COUNTERS["bioetl_errors_total"].labels().inc.assert_called_once_with(1)

    def test_histogram_and_gauge_paths_dispatch_to_registered_collectors(self) -> None:
        metrics = PrometheusMetrics()

        with patch.dict(HISTOGRAMS, {"bioetl_pipeline_duration_seconds": MagicMock()}):
            metrics.observe_histogram(
                "bioetl_pipeline_duration_seconds",
                12.5,
                {
                    "pipeline": "chembl_activity",
                    "stage": "extract",
                    "status": "success",
                    "run_type": "incremental",
                },
            )

            HISTOGRAMS[
                "bioetl_pipeline_duration_seconds"
            ].labels.assert_called_once_with(
                pipeline="chembl_activity",
                stage="extract",
                status="success",
                run_type="incremental",
            )
            HISTOGRAMS[
                "bioetl_pipeline_duration_seconds"
            ].labels().observe.assert_called_once_with(12.5)

        with patch.dict(GAUGES, {"bioetl_circuit_breaker_state": MagicMock()}):
            metrics.set_gauge(
                "bioetl_circuit_breaker_state",
                2.0,
                {"adapter": "chembl"},
            )

            GAUGES["bioetl_circuit_breaker_state"].labels.assert_called_once_with(
                adapter="chembl"
            )
            GAUGES["bioetl_circuit_breaker_state"].labels().set.assert_called_once_with(
                2.0
            )

    def test_unknown_metric_names_fail_loudly(self) -> None:
        metrics = PrometheusMetrics()

        with pytest.raises(ValueError, match="Unknown Prometheus counter metric"):
            metrics.increment_counter("unknown_counter", 1, {"label": "value"})

        with pytest.raises(ValueError, match="Unknown Prometheus histogram metric"):
            metrics.observe_histogram("unknown_histogram", 1.0, {"label": "value"})

        with pytest.raises(ValueError, match="Unknown Prometheus gauge metric"):
            metrics.set_gauge("unknown_gauge", 1.0, {"label": "value"})

    def test_noop_metrics_are_safe_and_close_is_idempotent(self) -> None:
        metrics = NoOpMetrics(warn_on_use=False)

        assert metrics.observe_histogram("metric", 1.0, {"pipeline": "chembl"}) is None
        assert metrics.increment_counter("metric", 1, {"pipeline": "chembl"}) is None
        assert metrics.set_gauge("metric", 1.0, {"pipeline": "chembl"}) is None
        assert metrics.close() is None
        assert metrics.close() is None
