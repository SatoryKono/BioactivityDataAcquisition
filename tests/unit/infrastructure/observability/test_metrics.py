"""Unit tests for Metrics adapters."""

from __future__ import annotations

import math
import warnings

import pytest

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.observability.prometheus_metrics import (
    COUNTERS,
    HISTOGRAMS,
    PrometheusMetrics,
)


class TestPrometheusMetrics:
    def test_observe_histogram_success(self):
        """Test observing a value for a valid histogram."""
        metrics = PrometheusMetrics()

        hist = HISTOGRAMS["bioetl_pipeline_duration_seconds"]
        # Correct labels based on metrics.py definition: ["pipeline", "stage", "status", "run_type"]
        labels = {
            "pipeline": "test_pipe",
            "stage": "transform",
            "status": "success",
            "run_type": "manual",
        }
        val = 15.5

        # Capture start value
        start_val = hist.labels(**labels)._sum.get()

        metrics.observe_histogram("bioetl_pipeline_duration_seconds", val, labels)

        # Verify delta
        end_val = hist.labels(**labels)._sum.get()
        assert math.isclose(end_val, start_val + val)

    def test_increment_counter_success(self):
        """Test incrementing a counter."""
        metrics = PrometheusMetrics()
        counter = COUNTERS["bioetl_records_processed_total"]

        # Correct labels based on metrics.py definition: ["pipeline", "stage", "run_type"]
        labels = {"pipeline": "test_pipe", "stage": "bronze", "run_type": "scheduled"}
        start_val = counter.labels(**labels)._value.get()

        metrics.increment_counter("bioetl_records_processed_total", 5, labels)

        end_val = counter.labels(**labels)._value.get()
        assert end_val == start_val + 5

    def test_invalid_metric_name_histogram(self):
        """Invalid histogram names must raise a contract error."""
        metrics = PrometheusMetrics()
        with pytest.raises(ValueError, match="Unknown Prometheus histogram metric"):
            metrics.observe_histogram("non_existent_metric", 10.0, {})

    def test_invalid_metric_name_counter(self):
        """Invalid counter names must raise a contract error."""
        metrics = PrometheusMetrics()
        with pytest.raises(ValueError, match="Unknown Prometheus counter metric"):
            metrics.increment_counter("non_existent_counter", 1, {})


class TestNoOpMetrics:
    def setup_method(self):
        """Reset warning state."""
        NoOpMetrics.reset_warning()

    def test_warning_on_init(self):
        """Test that a warning is issued when warn_on_use=True."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            NoOpMetrics(warn_on_use=True)
            assert len(w) == 1
            assert issubclass(w[0].category, UserWarning)
            assert "NoOpMetrics is being used" in str(w[0].message)

    def test_no_warning_explicit_opt_out(self):
        """Test that no warning is issued if warn_on_use=False."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            NoOpMetrics(warn_on_use=False)
            assert len(w) == 0

    def test_warning_only_once(self):
        """Test that the warning is only issued once globally."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            NoOpMetrics(warn_on_use=True)
            assert len(w) == 1

        # Second time should be silent
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            NoOpMetrics(warn_on_use=True)
            assert len(w) == 0

    def test_methods_do_nothing(self):
        """Ensure methods run without error."""
        metrics = NoOpMetrics(warn_on_use=False)
        metrics.observe_histogram("foo", 1.0, {})
        metrics.increment_counter("bar", 1, {})
