"""Shared default factory helpers for adapter wiring.

Provides create_default_error_handler() and create_default_fallback_service()
used by all provider adapters as fallback when dependencies are not injected
from the Composition Root.

Consolidates previously duplicated per-provider _create_default_*_error_handler
and _create_default_*_fallback_service functions (RF-002).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.common import FallbackFetchOrchestratorService

if TYPE_CHECKING:
    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics


def create_default_error_handler(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
) -> ErrorHandlerPort:
    """Create default adapter error handler for non-DI call sites.

    Returns:
        ErrorHandlerPort implementation configured with the given logger and metrics.
    """
    from bioetl.infrastructure.adapters.error_handling import ErrorService

    return ErrorService(logger, metrics=metrics)


def create_default_fallback_service(
    *,
    adapter_metrics: AdapterMetrics,
) -> FallbackFetchOrchestratorService:
    """Create fallback orchestrator service for non-DI call sites.

    Returns:
        FallbackFetchOrchestratorService instance wired to the given adapter metrics.
    """
    return FallbackFetchOrchestratorService(adapter_metrics)
