"""Shared metrics-service assembly helpers for composition bootstrap."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.metrics_service import MetricsService
from bioetl.infrastructure.observability.metrics_server_adapter import (
    MetricsServerAdapter,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

__all__ = ["create_metrics_service"]


def create_metrics_service(
    *,
    logger: LoggerPort | None = None,
) -> MetricsService:
    """Build a metrics service with a composition-owned server adapter."""
    resolved_logger = logger if logger is not None else NoOpLogger()
    return MetricsService(
        logger=resolved_logger,
        _server=MetricsServerAdapter(logger=resolved_logger),
    )
