"""Shared default factory helpers for adapter wiring.

Provides create_default_error_handler() and create_default_fallback_service()
used by all provider adapters as fallback when dependencies are not injected
from the Composition Root.

Consolidates previously duplicated per-provider _create_default_*_error_handler
and _create_default_*_fallback_service functions (RF-002).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.domain.ports import ErrorHandlerPort
from bioetl.infrastructure.adapters.common import FallbackFetchOrchestrator

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )


def create_default_error_handler(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
) -> ErrorHandlerPort:
    """Create default adapter error handler for non-DI call sites.

    Returns:
        ErrorHandlerPort implementation configured with the given logger and metrics.
    """
    from bioetl.infrastructure.adapters.error_handling import AdapterErrorHandler

    return cast("ErrorHandlerPort", AdapterErrorHandler(logger, metrics=metrics))


def create_default_fallback_service(
    *,
    adapter_metrics: AdapterMetricsRecorder,
) -> FallbackFetchOrchestrator:
    """Create fallback fetch orchestrator for non-DI call sites.

    Returns:
        FallbackFetchOrchestrator instance wired to the given adapter metrics.
    """
    return FallbackFetchOrchestrator(adapter_metrics)


def create_default_adapter_metrics(
    *,
    metrics: MetricsPort | None,
    provider: str,
) -> AdapterMetricsRecorder:
    """Create default adapter metrics helper for non-DI call sites."""
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder

    return AdapterMetricsRecorder(metrics, provider)


def create_default_request_collector() -> APIRequestCollector:
    """Create default request collector for non-DI call sites."""
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )

    return APIRequestCollector()
