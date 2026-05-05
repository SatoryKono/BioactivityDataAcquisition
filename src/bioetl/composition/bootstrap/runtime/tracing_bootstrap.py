"""Tracing bootstrap helpers for runtime observability wiring."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.domain.ports import TracingPort
from bioetl.domain.ports.noop import NoOpTracing
from bioetl.infrastructure.observability import OpenTelemetryTracer

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings

TracerFactory = Callable[[str], TracingPort]

__all__ = [
    "bootstrap_tracer",
]


def _default_tracer_factory(service_name: str) -> TracingPort:
    """Create OpenTelemetry tracer for the given service name."""
    return OpenTelemetryTracer(service_name=service_name)


def bootstrap_tracer(
    settings: Settings,
    service_name: str = "bioetl",
    tracer_factory: TracerFactory | None = None,
) -> TracingPort:
    """Create a tracing port implementation for distributed tracing.

    Args:
        settings: Application settings used to check whether tracing is enabled.
        service_name: OpenTelemetry service name used for span identification.
            Defaults to 'bioetl'.
        tracer_factory: Optional factory callable for DI/testing; uses
            OpenTelemetryTracer when None and tracing is enabled.

    Returns:
        Configured TracingPort, or NoOpTracing if tracing is disabled.
    """
    observability = getattr(settings, "observability", None)
    tracing_enabled = bool(getattr(observability, "tracing_enabled", False))
    if tracing_enabled:
        factory = tracer_factory or _default_tracer_factory
        return factory(service_name)
    return NoOpTracing()
