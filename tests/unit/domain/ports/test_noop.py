"""Tests for No-Op implementations of ports.

Tests the Null Object Pattern implementations for observability and utility ports.
"""

from __future__ import annotations

import pytest

from bioetl.domain.ports.noop import (
    NoOpMemoryMonitor,
    NoOpMetrics,
    NoOpPiiHasher,
    NoOpTracing,
    _NoOpOtelTracer,
    _NoOpSpan,
)


@pytest.mark.unit
class TestNoOpSpan:
    """Test _NoOpSpan class."""

    def test_context_manager_enter_returns_self(self) -> None:
        """Test __enter__ returns self."""
        span = _NoOpSpan()
        assert span.__enter__() is span

    def test_context_manager_exit_no_error(self) -> None:
        """Test __exit__ does nothing and returns None."""
        span = _NoOpSpan()
        result = span.__exit__(None, None, None)
        assert result is None

    def test_set_attribute_no_error(self) -> None:
        """Test set_attribute is a no-op."""
        span = _NoOpSpan()
        span.set_attribute("key", "value")  # Should not raise

    def test_set_status_no_error(self) -> None:
        """Test set_status is a no-op."""
        span = _NoOpSpan()
        span.set_status("OK")  # Should not raise

    def test_record_exception_no_error(self) -> None:
        """Test record_exception is a no-op."""
        span = _NoOpSpan()
        span.record_exception(ValueError("test"))  # Should not raise

    def test_add_event_no_error(self) -> None:
        """Test add_event is a no-op."""
        span = _NoOpSpan()
        span.add_event("bioetl.memory.decision", {"index": 1})  # Should not raise


@pytest.mark.unit
class TestNoOpOtelTracer:
    """Test _NoOpOtelTracer class."""

    def test_start_as_current_span_returns_noop_span(self) -> None:
        """Test start_as_current_span returns _NoOpSpan."""
        tracer = _NoOpOtelTracer()
        span = tracer.start_as_current_span("operation")
        assert isinstance(span, _NoOpSpan)

    def test_span_context_manager(self) -> None:
        """Test span can be used as context manager."""
        tracer = _NoOpOtelTracer()
        with tracer.start_as_current_span("op") as span:
            span.set_attribute("key", "value")
        assert isinstance(span, _NoOpSpan)


@pytest.mark.unit
class TestNoOpTracing:
    """Test NoOpTracing class."""

    def test_get_tracer_returns_noop_tracer(self) -> None:
        """Test get_tracer returns _NoOpOtelTracer."""
        tracing = NoOpTracing()
        tracer = tracing.get_tracer("test.module")
        assert isinstance(tracer, _NoOpOtelTracer)

    def test_close_no_error(self) -> None:
        """Test close is a no-op."""
        tracing = NoOpTracing()
        tracing.close()  # Should not raise

    def test_close_idempotent(self) -> None:
        """Test close can be called multiple times."""
        tracing = NoOpTracing()
        tracing.close()
        tracing.close()  # Should not raise

    def test_flush_no_error(self) -> None:
        """Test flush is a no-op."""
        tracing = NoOpTracing()
        tracing.flush()


@pytest.mark.unit
class TestNoOpMetrics:
    """Test NoOpMetrics class."""

    def test_observe_histogram_no_error(self) -> None:
        """Test observe_histogram is a no-op."""
        metrics = NoOpMetrics()
        metrics.observe_histogram("duration", 1.5, {"entity": "activity"})

    def test_increment_counter_no_error(self) -> None:
        """Test increment_counter is a no-op."""
        metrics = NoOpMetrics()
        metrics.increment_counter("errors", 1, {"type": "validation"})

    def test_set_gauge_no_error(self) -> None:
        """Test set_gauge is a no-op."""
        metrics = NoOpMetrics()
        metrics.set_gauge("memory_usage", 75.5, {"unit": "percent"})

    def test_metrics_reject_legacy__labels_alias(self) -> None:
        """Legacy _labels keyword should remain rejected."""
        metrics = NoOpMetrics()
        with pytest.raises(TypeError):
            metrics.observe_histogram("duration", 1.5, _labels={"entity": "activity"})
        with pytest.raises(TypeError):
            metrics.increment_counter("errors", 1, _labels={"type": "validation"})
        with pytest.raises(TypeError):
            metrics.set_gauge("memory_usage", 75.5, _labels={"unit": "percent"})

    def test_metrics_reject_legacy_tags_alias(self) -> None:
        """Legacy tags keyword should remain rejected."""
        metrics = NoOpMetrics()
        with pytest.raises(TypeError):
            metrics.observe_histogram("duration", 1.5, tags={"entity": "activity"})
        with pytest.raises(TypeError):
            metrics.increment_counter("errors", 1, tags={"type": "validation"})
        with pytest.raises(TypeError):
            metrics.set_gauge("memory_usage", 75.5, tags={"unit": "percent"})

    def test_close_no_error__test_no_op_metrics_domain_ports_test_noop_140(
        self,
    ) -> None:
        """Test close is a no-op."""
        metrics = NoOpMetrics()
        metrics.close()  # Should not raise

    def test_close_idempotent__test_no_op_metrics_domain_ports_test_noop_145(
        self,
    ) -> None:
        """Test close can be called multiple times."""
        metrics = NoOpMetrics()
        metrics.close()
        metrics.close()  # Should not raise


@pytest.mark.unit
class TestNoOpPiiHasher:
    """Test NoOpPiiHasher class."""

    def test_hash_value_returns_unchanged(self) -> None:
        """Test hash_value returns input unchanged."""
        hasher = NoOpPiiHasher()
        assert hasher.hash_value("test@example.com") == "test@example.com"

    def test_hash_value_handles_none(self) -> None:
        """Test hash_value handles None."""
        hasher = NoOpPiiHasher()
        assert hasher.hash_value(None) is None

    def test_hash_list_returns_unchanged(self) -> None:
        """Test hash_list returns input unchanged."""
        hasher = NoOpPiiHasher()
        values = ["a@b.com", "c@d.com"]
        assert hasher.hash_list(values) == values

    def test_hash_list_handles_none(self) -> None:
        """Test hash_list handles None."""
        hasher = NoOpPiiHasher()
        assert hasher.hash_list(None) is None

    def test_get_salt_id_returns_noop(self) -> None:
        """Test get_salt_id returns 'noop'."""
        hasher = NoOpPiiHasher()
        assert hasher.get_salt_id() == "noop"


@pytest.mark.unit
class TestNoOpMemoryMonitor:
    """Test NoOpMemoryMonitor class."""

    def test_get_memory_stats_returns_conservative(self) -> None:
        """Test get_memory_stats returns 50% usage."""
        monitor = NoOpMemoryMonitor()
        stats = monitor.get_memory_stats()
        assert stats.percent_used == pytest.approx(0.5)
        assert stats.used_mb == pytest.approx(4096.0)
        assert stats.available_mb == pytest.approx(4096.0)
        assert stats.total_mb == pytest.approx(8192.0)
        assert stats.process_mb == pytest.approx(256.0)

    def test_is_under_pressure_returns_false(self) -> None:
        """Test is_under_pressure returns False."""
        monitor = NoOpMemoryMonitor()
        assert monitor.is_under_pressure() is False

    def test_get_recommended_batch_size_returns_input(self) -> None:
        """Test get_recommended_batch_size returns input unchanged."""
        monitor = NoOpMemoryMonitor()
        assert monitor.get_recommended_batch_size(500) == 500
        assert monitor.get_recommended_batch_size(1000) == 1000

    def test_estimate_batch_memory_mb(self) -> None:
        """Test estimate_batch_memory_mb calculates correctly."""
        monitor = NoOpMemoryMonitor()
        # 1000 records * 1024 bytes * 2.5 overhead / 1024^2 = 2.44 MB
        result = monitor.estimate_batch_memory_mb(1000, 1024)
        expected = (1000 * 1024 * 2.5) / (1024 * 1024)
        assert result == pytest.approx(expected, abs=0.01)

    def test_calculate_max_batch_size_returns_large(self) -> None:
        """Test calculate_max_batch_size returns 10000."""
        monitor = NoOpMemoryMonitor()
        assert monitor.calculate_max_batch_size() == 10000
        assert monitor.calculate_max_batch_size(2048) == 10000
