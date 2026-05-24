"""Composition-owned helpers for resolving observability ports.

This module centralizes null-object fallback ownership for composition seams so
compatibility wrappers and factories do not each re-encode observability
defaults independently.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.ports import MetricsPort, TracingPort
from bioetl.domain.ports.noop import NoOpMetrics, NoOpTracing

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = ["resolve_metrics_port", "resolve_tracing_port"]


def resolve_metrics_port(
    *,
    metrics: MetricsPort | None,
    settings: Settings | None = None,
) -> MetricsPort:
    """Return an explicit metrics port for composition-owned wiring.

    Preference order:
    1. use the injected metrics port when provided;
    2. derive the canonical runtime metrics port from settings;
    3. fall back to a composition-owned NoOpMetrics.
    """
    if metrics is not None:
        return metrics
    if settings is not None:
        from bioetl.composition.bootstrap.runtime.metrics_bootstrap import (
            bootstrap_metrics,
        )

        return bootstrap_metrics(settings)
    return NoOpMetrics(warn_on_use=False)


def resolve_tracing_port(
    *,
    tracer: TracingPort | None,
    settings: Settings | None = None,
    service_name: str = "bioetl",
) -> TracingPort:
    """Return an explicit tracing port for composition-owned wiring.

    Preference order:
    1. use the injected tracing port when provided;
    2. derive the canonical runtime tracing port from settings;
    3. fall back to a composition-owned NoOpTracing.
    """
    if tracer is not None:
        return tracer
    if settings is not None:
        from bioetl.composition.bootstrap.runtime.observability import (
            bootstrap_tracer,
        )

        return bootstrap_tracer(settings, service_name=service_name)
    return NoOpTracing()
