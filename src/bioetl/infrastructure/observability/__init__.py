"""Observability infrastructure: logging, metrics, anomaly detection, lineage.

This is the single source of truth for all observability components.
Import individual modules directly to avoid loading unnecessary dependencies:

    # Structured logging
    from bioetl.infrastructure.observability.logging import create_logger

    # Prometheus metrics
    from bioetl.infrastructure.observability.metrics import MetricsCollector

    # Anomaly detection
    from bioetl.infrastructure.observability.anomaly import AnomalyDetector

    # Data lineage tracking
    from bioetl.infrastructure.observability.lineage import LineageTracker
"""

# Lazy imports - individual modules should be imported directly
__all__ = [
    "anomaly",
    "lineage",
    "logging",
    "metrics",
]
