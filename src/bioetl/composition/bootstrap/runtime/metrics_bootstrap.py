"""Metrics bootstrap helpers for runtime observability wiring."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.application.services.metrics_service import MetricsService
from bioetl.composition.bootstrap.assembly.metrics_service import (
    create_metrics_service,
)
from bioetl.domain.ports import MetricsPort
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.observability import PrometheusMetrics

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings

MetricsFactory = Callable[[], MetricsPort]
MetricsServiceFactory = Callable[..., MetricsService]

__all__ = [
    "bootstrap_metrics_port",
    "maybe_start_metrics_server",
]


def _metrics_enabled(settings: object) -> bool:
    """Support both nested Settings.observability and legacy flat test doubles."""
    observability = getattr(settings, "observability", None)
    if observability is not None and hasattr(observability, "metrics_enabled"):
        return bool(observability.metrics_enabled)
    return bool(getattr(settings, "metrics_enabled", False))


def bootstrap_metrics_port(
    settings: Settings,
    metrics_factory: MetricsFactory | None = None,
) -> MetricsPort:
    """Create a metrics port implementation.

    Args:
        settings: Application settings used to check whether metrics are enabled.
        metrics_factory: Optional factory callable for DI/testing; uses PrometheusMetrics
            when None and metrics are enabled.

    Returns:
        Configured MetricsPort, or NoOpMetrics if metrics are disabled.
    """
    if not _metrics_enabled(settings):
        return NoOpMetrics(warn_on_use=False)

    factory = metrics_factory or PrometheusMetrics
    return factory()


def maybe_start_metrics_server(
    settings: Settings,
    metrics_service_factory: MetricsServiceFactory | None = None,
) -> bool:
    """Start metrics server if enabled in settings.

    Args:
        settings: Application settings providing metrics port, address, and flags.
        metrics_service_factory: Optional composition-owned service bootstrapper;
            uses the default shared ``create_metrics_service`` when None.

    Returns:
        True if the metrics server was started, False otherwise.
    """
    if not _metrics_enabled(settings):
        return False

    observability = getattr(settings, "observability", None)
    if observability is None:
        return False

    if not observability.metrics_server_enabled:
        return False

    obs = observability
    service_factory = metrics_service_factory or create_metrics_service
    service = service_factory()
    result = service.start(
        port=settings.metrics_port,
        addr=settings.metrics_addr,
        fail_fast=obs.metrics_fail_fast,
        retry_count=obs.metrics_retry_count,
        retry_delay=obs.metrics_retry_delay,
    )
    return bool(result.success)
