"""Explicit TracingPort contract suite."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.domain.ports import TracingPort
from bioetl.domain.ports.noop import NoOpTracing


@pytest.mark.unit
class TestTracingPortContract:
    """Bounded contract assertions for TracingPort implementations."""

    def test_noop_tracing_implements_tracing_port(self) -> None:
        assert isinstance(NoOpTracing(), TracingPort)

    def test_noop_tracing_span_path_is_safe(self) -> None:
        """NoOpTracing must expose an OTel-like span path without side effects."""
        tracing = NoOpTracing()
        tracer = tracing.get_tracer("bioetl.contracts")

        with tracer.start_as_current_span(
            "demo",
            attributes={"bioetl.run_id": "run-123"},
        ) as span:
            assert span is not None
            assert span.set_attribute("bioetl.status", "success") is None
            assert span.record_exception(RuntimeError("boom")) is None

        assert tracing.flush() is None
        assert tracing.close() is None
        assert tracing.close() is None

    def test_open_telemetry_tracer_wraps_span_context_manager(self) -> None:
        """One canonical span path must forward into the underlying tracer."""
        from bioetl.infrastructure.observability import tracing as tracing_module

        if not tracing_module.OTEL_AVAILABLE:
            pytest.skip("OpenTelemetry is not available")

        entered_span = MagicMock()
        context_manager = MagicMock()
        context_manager.__enter__.return_value = entered_span
        context_manager.__exit__.return_value = None
        otel_tracer = MagicMock()
        otel_tracer.start_as_current_span.return_value = context_manager

        original_get_tracer = tracing_module.trace.get_tracer
        tracing_module.trace.get_tracer = MagicMock(return_value=otel_tracer)
        tracer_port = tracing_module.OpenTelemetryTracer("bioetl-contract-tests")
        try:
            assert isinstance(tracer_port, TracingPort)

            span_handle = tracer_port.get_tracer("bioetl.contracts").start_as_current_span(
                "pipeline.run",
                attributes={"bioetl.run_id": "run-123"},
            )

            with span_handle as span:
                span.set_attribute("bioetl.status", "success")
                span.record_exception(RuntimeError("boom"))

            otel_tracer.start_as_current_span.assert_called_once_with(
                "pipeline.run",
                attributes={"bioetl.run_id": "run-123"},
            )
            entered_span.set_attribute.assert_called_once_with(
                "bioetl.status",
                "success",
            )
            entered_span.record_exception.assert_called_once()
        finally:
            tracing_module.trace.get_tracer = original_get_tracer
            tracer_port.close()
