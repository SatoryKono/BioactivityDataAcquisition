"""Infrastructure layer observability components.

This package contains implementations of observability ports:
- Metrics (Prometheus)
- Tracing (OpenTelemetry - optional)
- Logging (Structlog integration)
- Health Checks

Implements RULES.md §3 (Observability).
"""

from __future__ import annotations

from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.observability.noop_tracing import NoOpTracing
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.observability.tracing import OpenTelemetryTracer

__all__ = [
    "NoOpMetrics",
    "NoOpTracing",
    "OpenTelemetryTracer",
    "PrometheusMetrics",
]
