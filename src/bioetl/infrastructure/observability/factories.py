"""Factories for observability adapters."""

from __future__ import annotations

import structlog

from bioetl.infrastructure.observability.adapters import (
    StructuredLoggerImpl,
    TracingAdapterImpl,
)
from bioetl.interfaces.observability import LoggingPortABC, TracingPortABC


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


__all__ = [
    "default_logging_port",
    "default_tracing_port",
]
