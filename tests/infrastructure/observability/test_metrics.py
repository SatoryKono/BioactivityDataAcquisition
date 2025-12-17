"""Unit tests for Metrics adapters."""

import warnings
from unittest.mock import MagicMock, patch

import pytest

from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.observability.prometheus_metrics import (
    COUNTERS,
    HISTOGRAMS,
    PrometheusMetrics,
)


class TestPrometheusMetrics:
    def test_observe_histogram_success(self):
        """Test observing a value for a valid histogram."""
        metrics = PrometheusMetrics()

        hist = HISTOGRAMS["pipeline_duration_seconds"]
        labels = {"pipeline_name": "test_pipe", "run_type": "manual", "status": "success"}
        val = 15.5

        # Capture start value
        start_val = hist.labels(**labels)._sum.get()

        metrics.observe_histogram("pipeline_duration_seconds", val, labels)

        # Verify delta
        end_val = hist.labels(**labels)._sum.get()
        assert end_val == start_val + val

    def test_increment_counter_success(self):
        """Test incrementing a counter."""
        metrics = PrometheusMetrics()
        counter = COUNTERS["records_processed_total"]

        labels = {"pipeline_name": "test_pipe", "run_type": "scheduled", "layer": "bronze"}
        start_val = counter.labels(**labels)._value.get()

        metrics.increment_counter("records_processed_total", 5, labels)

        end_val = counter.labels(**labels)._value.get()
        assert end_val == start_val + 5

    def test_invalid_metric_name_histogram(self):
        """Test that invalid histogram names are ignored or raise error (code ignores currently)."""
        metrics = PrometheusMetrics()
        metrics.observe_histogram("non_existent_metric", 10.0, {})

    def test_invalid_metric_name_counter(self):
        """Test that invalid counter names are ignored."""
        metrics = PrometheusMetrics()
        metrics.increment_counter("non_existent_counter", 1, {})


class TestNoOpMetrics:
    def setup_method(self):
        """Reset warning state."""
        NoOpMetrics.reset_warning()

    def test_warning_on_init(self):
        """Test that a warning is issued when initialized by default."""
        with pytest.warns(UserWarning, match="NoOpMetrics is being used"):
            NoOpMetrics()

    def test_no_warning_explicit_opt_out(self):
        """Test that no warning is issued if warn_on_use=False."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            NoOpMetrics(warn_on_use=False)
            assert len(w) == 0

    def test_warning_only_once(self):
        """Test that the warning is only issued once globally."""
        with pytest.warns(UserWarning):
            NoOpMetrics()

        # Second time should be silent
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            NoOpMetrics()
            assert len(w) == 0

    def test_methods_do_nothing(self):
        """Ensure methods run without error."""
        metrics = NoOpMetrics(warn_on_use=False)
        metrics.observe_histogram("foo", 1.0, {})
        metrics.increment_counter("bar", 1, {})
