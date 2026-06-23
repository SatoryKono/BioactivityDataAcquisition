"""Prometheus Metrics facade for BioETL."""

from __future__ import annotations

from bioetl.infrastructure.observability import metrics_definitions as _definitions
from bioetl.infrastructure.observability.metrics_collector import MetricsCollector
from bioetl.infrastructure.observability.metrics_export_names import (
    METRICS_DEFINITION_EXPORT_NAMES,
)
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics

globals().update(
    {name: getattr(_definitions, name) for name in METRICS_DEFINITION_EXPORT_NAMES}
)

__all__ = [*METRICS_DEFINITION_EXPORT_NAMES, "MetricsCollector", "PrometheusMetrics"]
