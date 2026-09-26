"""Prometheus Metrics facade for BioETL."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.observability import metrics_definitions as _definitions
from bioetl.infrastructure.observability.metrics_collector import MetricsCollector
from bioetl.infrastructure.observability.metrics_export_names import (
    METRICS_DEFINITION_EXPORT_NAMES,
)
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics

if TYPE_CHECKING:
    from bioetl.infrastructure.observability.metrics_definitions import (
        GOLD_LIFECYCLE_STATE_TOTAL as GOLD_LIFECYCLE_STATE_TOTAL,
    )
    from bioetl.infrastructure.observability.metrics_definitions import (
        GOLD_VALIDATION_FAILURES_TOTAL as GOLD_VALIDATION_FAILURES_TOTAL,
    )
    from bioetl.infrastructure.observability.metrics_definitions import (
        GOLD_WRITE_ATTEMPTS_TOTAL as GOLD_WRITE_ATTEMPTS_TOTAL,
    )
    from bioetl.infrastructure.observability.metrics_definitions import (
        GOLD_WRITE_DURATION_SECONDS as GOLD_WRITE_DURATION_SECONDS,
    )
    from bioetl.infrastructure.observability.metrics_definitions import (
        GOLD_WRITE_OUTCOMES_TOTAL as GOLD_WRITE_OUTCOMES_TOTAL,
    )

globals().update(
    {name: getattr(_definitions, name) for name in METRICS_DEFINITION_EXPORT_NAMES}
)

__all__ = [*METRICS_DEFINITION_EXPORT_NAMES, "MetricsCollector", "PrometheusMetrics"]
