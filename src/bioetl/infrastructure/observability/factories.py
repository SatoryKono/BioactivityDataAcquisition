"""Factories for observability adapters.

Naming convention:
- create_*() - creates a new instance each time
- get_*() - returns singleton/cached instance
- build_*() - uses builder pattern
"""

from __future__ import annotations

import structlog

from bioetl.domain.observability.contracts import (
    LoggingPortABC,
    MetricsPortABC,
    TracingPortABC,
)
from bioetl.infrastructure.observability.adapters import (
    PrometheusMetricsPortImpl,
    StructuredLoggerImpl,
    TracingAdapterImpl,
)


def _configure_structlog() -> None:
    if structlog.is_configured():
        return
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )


def create_logging_port() -> LoggingPortABC:
    """Create a new configured structured logger adapter."""
    _configure_structlog()
    return StructuredLoggerImpl()


def create_tracing_port() -> TracingPortABC:
    """Create a new tracing adapter instance."""
    return TracingAdapterImpl()


def create_metrics_port() -> MetricsPortABC:
    """Create a new Prometheus-backed metrics port."""
    return PrometheusMetricsPortImpl()


__all__ = [
    "create_logging_port",
    "create_metrics_port",
    "create_tracing_port",
]
