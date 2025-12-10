"""Factories for observability adapters."""

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


def default_logging_port() -> LoggingPortABC:
    """Create configured structured logger adapter."""
    _configure_structlog()
    return StructuredLoggerImpl()


def default_tracing_port() -> TracingPortABC:
    """Return tracing adapter implementation."""
    return TracingAdapterImpl()


def default_metrics_port() -> MetricsPortABC:
    """Create Prometheus-backed metrics port."""

    return PrometheusMetricsPortImpl()


__all__ = [
    "default_logging_port",
    "default_metrics_port",
    "default_tracing_port",
]
