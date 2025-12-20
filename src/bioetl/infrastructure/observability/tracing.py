"""Tracing implementations (OpenTelemetry).

Implements TracingPort.
"""

from typing import Any

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )

    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
    except ImportError:
        OTLPSpanExporter = None

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class OpenTelemetryTracer:
    """Real OpenTelemetry tracer implementation."""

    def __init__(self, service_name: str = "bioetl"):
        if not OTEL_AVAILABLE:
            raise ImportError(
                "OpenTelemetry is not installed. Install with 'pip install opentelemetry-api opentelemetry-sdk'"
            )

        provider = TracerProvider()

        # Prefer OTLP if available (production), fall back to Console (dev/debug)
        if OTLPSpanExporter:
            exporter = OTLPSpanExporter()
        else:
            exporter = ConsoleSpanExporter()

        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer(service_name)

    def get_tracer(self, name: str) -> Any:
        return trace.get_tracer(name)


class NoOpTracer:
    """Null object pattern for tracing."""

    def get_tracer(self, name: str) -> Any:
        """Return a dummy object that swallows calls."""

        class DummySpan:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def set_attribute(self, *args): pass
            def add_event(self, *args): pass
            def record_exception(self, *args): pass

        class DummyTracer:
            def start_as_current_span(self, *args, **kwargs):
                return DummySpan()

        return DummyTracer()
