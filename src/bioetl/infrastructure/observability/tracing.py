"""OpenTelemetry tracer adapter — real TracingPort implementation.

TracingPort is deliberately shaped as an OpenTelemetry Tracing API facade
(see ADR-017, ADR-022).  This module provides ``OpenTelemetryTracer`` — the
concrete adapter that delegates to the OTel SDK.

Design Decision (ADR-010, ADR-022):
    Local-Only Deployment does not require distributed tracing by default.
    ``NoOpTracing`` (in ``domain/ports/noop.py``) is the zero-overhead default.
    ``OpenTelemetryTracer`` activates when ``tracing_enabled=True`` and
    provides real span collection via OTLP or Console exporter.

    Both implementations expose the same OTel-compatible API surface
    (``get_tracer → start_as_current_span → Span``), so switching between
    them requires no application code changes — only composition wiring.

Correlation:
    Instead of trace_id, run_id is used (RULES.md §4.5).
    All structured logs include run_id for request correlation.

Extension Point:
    To enable tracing, set ``BIOETL_OBSERVABILITY__TRACING_ENABLED=true``.
    The composition layer (``bootstrap_tracer_port``) will return
    ``OpenTelemetryTracer`` instead of ``NoOpTracing``.

Implements TracingPort (OTel facade).
"""

from __future__ import annotations

from typing import Any

from bioetl.domain.ports import NoOpTracing

# Store OTLP exporter class if available (for runtime use)
# This avoids reassigning an imported type to None, which mypy strict rejects
_OtlpExporterClass: type[Any] | None = None

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        _OtlpExporterClass = OTLPSpanExporter
        OTLP_AVAILABLE = True
    except ImportError:
        OTLP_AVAILABLE = False

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    OTLP_AVAILABLE = False


class OpenTelemetryTracer:
    """Concrete TracingPort adapter backed by the OpenTelemetry SDK.

    This is the "real" half of the OTel facade: ``get_tracer()`` delegates
    to ``opentelemetry.trace.get_tracer()``, returning a genuine OTel
    ``Tracer`` that creates exportable spans.  The port contract (TracingPort)
    is intentionally aligned with the OTel API, so this adapter is a thin
    wrapper rather than a translation layer.
    """

    def __init__(self, service_name: str = "bioetl") -> None:
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
        exporter = (
            _OtlpExporterClass()
            if OTLP_AVAILABLE and _OtlpExporterClass is not None
            else ConsoleSpanExporter()
        )

        processor = BatchSpanProcessor(exporter)
        self._provider.add_span_processor(processor)
        trace.set_tracer_provider(self._provider)
        self._tracer = trace.get_tracer(service_name)
        self._closed = False

    def get_tracer(self, name: str) -> Any:  # Any: returns OTel Tracer wh...
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
