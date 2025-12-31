"""Tracing infrastructure — Null Object Pattern implementation.

Design Decision (ADR-010, ADR-022):
    Local-Only Deployment does not require distributed tracing.
    NoOpTracing (default) provides:
    - Compliance with TracingPort interface
    - Extension point for future distributed deployment
    - Zero overhead in current configuration

Correlation:
    Instead of trace_id, run_id is used (RULES.md §4.5).
    All structured logs include run_id for request correlation.

Extension Point:
    To enable tracing, use OpenTelemetryTracer (provided below),
    register in composition/factories/observability.py.

Available Implementations:
    - NoOpTracing: Null Object Pattern, default for Local-Only
    - OpenTelemetryTracer: Real OTel implementation (requires opentelemetry deps)

Implements TracingPort.
"""

from __future__ import annotations

from typing import Any

from bioetl.infrastructure.observability.noop_tracing import NoOpTracing

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        OTLP_AVAILABLE = True
    except ImportError:
        OTLPSpanExporter = None
        OTLP_AVAILABLE = False

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    OTLP_AVAILABLE = False


class OpenTelemetryTracer:
    """Real OpenTelemetry tracer implementation."""

    def __init__(self, service_name: str = "bioetl"):
        """Initialize OpenTelemetry tracer.

        Args:
            service_name: Name of the service.

        Raises:
            ImportError: If opentelemetry is not installed.

        """
        if not OTEL_AVAILABLE:
            raise ImportError(
                "OpenTelemetry is not installed. Install with 'pip install opentelemetry-api opentelemetry-sdk'"
            )

        self._provider = TracerProvider()

        # Prefer OTLP if available (production), fall back to Console (dev/debug)
        exporter = OTLPSpanExporter() if OTLP_AVAILABLE else ConsoleSpanExporter()

        processor = BatchSpanProcessor(exporter)
        self._provider.add_span_processor(processor)
        trace.set_tracer_provider(self._provider)
        self._tracer = trace.get_tracer(service_name)
        self._closed = False

    def get_tracer(self, name: str) -> Any:
        """Get an OpenTelemetry tracer.

        Args:
            name: Name of the tracer.

        Returns:
            OpenTelemetry tracer instance.

        """
        return trace.get_tracer(name)

    def close(self) -> None:
        """Flush pending spans and shutdown provider. Idempotent."""
        if self._closed:
            return
        try:
            # Force flush with 5 second timeout
            self._provider.force_flush(timeout_millis=5000)
            self._provider.shutdown()
        except Exception:  # nosec B110
            # Best effort - don't fail the pipeline on tracing cleanup
            pass
        self._closed = True


# Re-export NoOpTracing for backward compatibility and testing
__all__ = ["NoOpTracing", "OpenTelemetryTracer"]
