"""Shared metrics-service assembly helpers for composition bootstrap."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.metrics_service import MetricsService
from bioetl.infrastructure.observability.metrics_publisher_adapter import (
    MetricsPublisherAdapter,
)
from bioetl.infrastructure.observability.metrics_server_adapter import (
    MetricsServerAdapter,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, TracingPort

__all__ = ["create_metrics_service"]


def create_metrics_service(
    *,
    logger: LoggerPort | None = None,
    tracer: TracingPort | None = None,
) -> MetricsService:
    """Build a metrics service with a composition-owned server adapter."""
    resolved_logger = logger if logger is not None else NoOpLogger()
    return MetricsService(
        logger=resolved_logger,
        clock=SystemClock(),
        tracer=tracer,
        _server=MetricsServerAdapter(logger=resolved_logger),
        _publisher=MetricsPublisherAdapter(logger=resolved_logger),
    )
