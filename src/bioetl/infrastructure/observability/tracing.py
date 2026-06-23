"""OpenTelemetry tracer adapter — real TracingPort implementation.

TracingPort is deliberately shaped as an OpenTelemetry Tracing API facade
(see ADR-017, ADR-022).  This module provides ``OpenTelemetryTracer`` — the
concrete adapter that delegates to the OTel SDK.

Design Decision (ADR-010, ADR-022):
    Local-Only Deployment does not require distributed tracing by default.
    ``NoOpTracing`` (in ``domain/ports/noop/__init__.py``) is the zero-overhead
    default.
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
    The composition layer (``bootstrap_tracer``) will return
    ``OpenTelemetryTracer`` instead of ``NoOpTracing``.

Implements TracingPort (OTel facade).
"""

from __future__ import annotations

import os
from contextlib import suppress
from typing import Any, Protocol, cast
from urllib.parse import urlparse

from bioetl.domain.ports.noop import NoOpTracing

# Store OTLP exporter class if available (for runtime use)
# This avoids reassigning an imported type to None, which mypy strict rejects
_OtlpExporterClass: (
    type[
        Any  # Any: OTel exporter class resolved at runtime
    ]
    | None
) = None

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
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


_LOCAL_OTLP_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "host.docker.internal",
    "tempo",
}


class _SpanProtocol(Protocol):
    """Minimal span surface used by BioETL tracing helpers."""

    def set_attribute(self, key: str, value: object) -> None: ...

    def record_exception(self, exception: Exception) -> None: ...


class _SpanContextManagerProtocol(Protocol):
    """Context manager returned by OTel tracer implementations."""

    def __enter__(self) -> _SpanProtocol: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> object | None: ...


class _TracerProtocol(Protocol):
    """Minimal tracer surface required by the adapter wrapper."""

    def start_as_current_span(
        self,
        name: str,
        *args: object,
        **kwargs: object,
    ) -> _SpanContextManagerProtocol: ...


class _SpanHandle:
    """Compatibility wrapper exposing span methods on OTel context managers."""

    def __init__(
        self,
        context_manager: _SpanContextManagerProtocol,
    ) -> None:
        self._context_manager = context_manager
        self._span: _SpanProtocol | None = None

    def __enter__(self) -> _SpanHandle:
        self._span = self._context_manager.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> object | None:
        return self._context_manager.__exit__(exc_type, exc_val, exc_tb)

    def set_attribute(self, key: str, value: object) -> None:
        if self._span is not None:
            self._span.set_attribute(key, value)

    def record_exception(self, exception: Exception) -> None:
        if self._span is not None:
            self._span.record_exception(exception)


class _TracerAdapter:
    """Adapter returning span handles compatible with BioETL tracing helpers."""

    def __init__(
        self,
        otel_tracer: _TracerProtocol,
    ) -> None:
        self._otel_tracer = otel_tracer

    def start_as_current_span(
        self,
        name: str,
        *,
        attributes: dict[str, object] | None = None,
    ) -> _SpanHandle:
        return _SpanHandle(
            self._otel_tracer.start_as_current_span(
                name,
                attributes={} if attributes is None else attributes,
            )
        )


def _parse_bool_env(raw_value: str) -> bool:
    """Interpret conventional truthy env values."""
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _extract_endpoint_host(endpoint: str) -> str:
    """Return the hostname portion from OTLP endpoint-like strings."""
    normalized = endpoint.strip()
    if "://" in normalized:
        return (urlparse(normalized).hostname or "").lower()
    if normalized.startswith("[") and "]" in normalized:
        return normalized[1:].split("]", 1)[0].lower()
    if normalized.count(":") == 1:
        normalized = normalized.rsplit(":", 1)[0]
    return normalized.strip("[]").lower()


def _get_otlp_endpoint() -> str | None:
    """Return the traces OTLP endpoint, preferring trace-specific env vars."""
    for env_name in (
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
    ):
        value = os.getenv(env_name, "").strip()
        if value:
            return value
    return None


def _get_otlp_insecure_setting() -> str | None:
    """Return explicit insecure override when configured by the user."""
    for env_name in (
        "OTEL_EXPORTER_OTLP_TRACES_INSECURE",
        "OTEL_EXPORTER_OTLP_INSECURE",
    ):
        value = os.getenv(env_name, "").strip()
        if value:
            return value
    return None


def _build_telemetry_exporter() -> (
    Any  # Any: exporter type depends on runtime-selected telemetry backend.
):
    # Any: exporter implementation is selected dynamically between console and OTLP classes.
    # Any: exporter class is selected dynamically between console and OTLP implementations.
    """Create the most appropriate tracing exporter for the current runtime."""
    if not OTLP_AVAILABLE or _OtlpExporterClass is None:
        return ConsoleSpanExporter()

    exporter_kwargs: dict[str, str | bool] = {}
    endpoint = _get_otlp_endpoint()
    insecure_override = _get_otlp_insecure_setting()
    if endpoint is not None:
        exporter_kwargs["endpoint"] = endpoint
        if insecure_override is not None:
            exporter_kwargs["insecure"] = _parse_bool_env(insecure_override)
        elif _extract_endpoint_host(endpoint) in _LOCAL_OTLP_HOSTS:
            exporter_kwargs["insecure"] = True
    elif insecure_override is not None:
        exporter_kwargs["insecure"] = _parse_bool_env(insecure_override)

    return _OtlpExporterClass(**exporter_kwargs)


def _resolve_service_name(default_service_name: str) -> str:
    """Return the configured OTel service name for emitted spans."""
    override = os.getenv("OTEL_SERVICE_NAME", "").strip()
    if override:
        return override
    return default_service_name


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

        resolved_service_name = _resolve_service_name(service_name)
        self._provider = TracerProvider(
            resource=Resource.create({"service.name": resolved_service_name})
        )

        # Prefer OTLP if available (production), fall back to Console (dev/debug)
        exporter = _build_telemetry_exporter()

        processor = BatchSpanProcessor(exporter)
        self._provider.add_span_processor(processor)
        trace.set_tracer_provider(self._provider)
        self._tracer = trace.get_tracer(resolved_service_name)
        self._closed = False

    def get_tracer(self, name: str) -> Any:  # Any: returns OTel Tracer wh...
        """Get an OpenTelemetry tracer.

        Args:
            name: Name of the tracer.

        Returns:
            OpenTelemetry tracer instance.

        """
        return _TracerAdapter(cast(_TracerProtocol, trace.get_tracer(name)))

    def flush(self) -> None:
        """Force-flush pending spans without shutting down the provider."""
        if self._closed:
            return
        with suppress(RuntimeError, OSError, ValueError, TypeError, AttributeError):
            self._provider.force_flush(timeout_millis=5000)

    def close(self) -> None:
        """Flush pending spans and shutdown provider. Idempotent."""
        if self._closed:
            return
        try:
            self.flush()
            self._provider.shutdown()
        except (RuntimeError, OSError, ValueError, TypeError, AttributeError):  # nosec B110
            # Best effort - don't fail the pipeline on tracing cleanup
            pass
        self._closed = True


# Re-export NoOpTracing for backward compatibility and testing
__all__ = ["NoOpTracing", "OpenTelemetryTracer"]
