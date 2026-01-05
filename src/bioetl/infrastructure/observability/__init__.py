"""Infrastructure layer observability components.

This package contains implementations of observability ports:
- Metrics (Prometheus)
- Tracing (OpenTelemetry - optional)
- Logging (Structlog integration)
- Health Checks

Implements RULES.md §3 (Observability).

For new code, prefer UnifiedLogger which enforces Log Schema (§3.2.1)
with mandatory fields: ts, level, run_id, pipeline, stage.
"""

from __future__ import annotations

from bioetl.infrastructure.observability.logging import StructlogLogger
from bioetl.infrastructure.observability.metrics_server_adapter import (
    MetricsServerAdapter,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.observability.noop_tracing import NoOpTracing
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.observability.tracing import OpenTelemetryTracer
from bioetl.infrastructure.observability.unified_logger import (
    UnifiedLogger,
    create_unified_logger,
)

__all__ = [
    "MetricsServerAdapter",
    "NoOpLogger",
    "NoOpMetrics",
    "NoOpTracing",
    "OpenTelemetryTracer",
    "PrometheusMetrics",
    "StructlogLogger",
    "UnifiedLogger",
    "create_unified_logger",
]
