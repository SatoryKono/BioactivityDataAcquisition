"""Metrics bootstrap helpers for runtime observability wiring."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.domain.ports import MetricsPort, NoOpMetrics
from bioetl.infrastructure.observability import PrometheusMetrics, start_metrics_server

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings

MetricsFactory = Callable[[], MetricsPort]
MetricsServerStarter = Callable[..., bool]

__all__ = [
    "bootstrap_metrics_port",
    "maybe_start_metrics_server",
]


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
    if not settings.observability.metrics_enabled:
        return NoOpMetrics(warn_on_use=False)

    factory = metrics_factory or PrometheusMetrics
    return factory()


def maybe_start_metrics_server(
    settings: Settings,
    start_server: MetricsServerStarter | None = None,
) -> bool:
    """Start metrics server if enabled in settings.

    Args:
        settings: Application settings providing metrics port, address, and flags.
        start_server: Optional callable to start the metrics HTTP server; uses the
            default infrastructure ``start_metrics_server`` when None.

    Returns:
        True if the metrics server was started, False otherwise.
    """
    if not settings.observability.metrics_enabled:
        return False

    if not settings.observability.metrics_server_enabled:
        return False

    obs = settings.observability
    starter = start_server or start_metrics_server
    return starter(
        port=settings.metrics_port,
        addr=settings.metrics_addr,
        fail_fast=obs.metrics_fail_fast,
        retry_count=obs.metrics_retry_count,
        retry_delay=obs.metrics_retry_delay,
    )
