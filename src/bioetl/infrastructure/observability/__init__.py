"""Observability adapters and factory exports."""

from bioetl.infrastructure.observability.adapters import (
    PrometheusMetricsPortImpl,
    StructuredLoggerImpl,
    TracingAdapterImpl,
)
from bioetl.infrastructure.observability.factories import (  # Deprecated aliases for backward compatibility
    create_logging_port,
    create_metrics_port,
    create_tracing_port,
    default_logging_port,
    default_metrics_port,
    default_tracing_port,
)

__all__ = [
    "StructuredLoggerImpl",
    "PrometheusMetricsPortImpl",
    "TracingAdapterImpl",
    # New naming convention
    "create_logging_port",
    "create_metrics_port",
    "create_tracing_port",
    # Deprecated aliases
    "default_logging_port",
    "default_metrics_port",
    "default_tracing_port",
]
