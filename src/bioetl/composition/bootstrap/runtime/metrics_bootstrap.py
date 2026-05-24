"""Metrics bootstrap helpers for runtime observability wiring."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.ports.observability import MetricsPort
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings

MetricsFactory = Callable[[], MetricsPort]
MetricsServiceFactory = Callable[..., object]

__all__ = [
    "bootstrap_metrics",
    "create_metrics_service",
    "maybe_start_metrics_server",
    "resolve_metrics_fail_fast",
]


def _metrics_enabled(settings: object) -> bool:
    """Support both nested Settings.observability and legacy flat test doubles."""
    observability = getattr(settings, "observability", None)
    if observability is not None and hasattr(observability, "metrics_enabled"):
        return bool(observability.metrics_enabled)
    return bool(getattr(settings, "metrics_enabled", False))


def _is_production_launcher(settings: object) -> bool:
    """Return True when the runtime launcher is executing in production mode."""
    env = getattr(settings, "env", None)
    test_mode = getattr(settings, "test_mode", False)
    test_mode_enabled = test_mode if isinstance(test_mode, bool) else False
    return env == "prod" and not test_mode_enabled


def _observability_field_explicitly_set(
    observability: object | None,
    field_name: str,
) -> bool:
    """Return True when a pydantic settings field was explicitly configured."""
    fields_set: object = getattr(observability, "model_fields_set", frozenset())
    return isinstance(fields_set, (set, frozenset)) and field_name in fields_set


def resolve_metrics_fail_fast(settings: Settings) -> bool:
    """Resolve metrics startup fail-fast policy for runtime launcher paths.

    Production launchers default to fail-fast metrics startup unless operators
    explicitly configure ``observability.metrics_fail_fast``. Non-production
    launchers keep the declared setting value.
    """
    observability = getattr(settings, "observability", None)
    configured_fail_fast = bool(getattr(observability, "metrics_fail_fast", False))
    if _is_production_launcher(settings) and not _observability_field_explicitly_set(
        observability,
        "metrics_fail_fast",
    ):
        return True
    return configured_fail_fast


def bootstrap_metrics(
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


def create_metrics_service(*args: object, **kwargs: object) -> object:
    """Compat seam for runtime tests patching metrics-service creation."""
    from bioetl.composition.bootstrap.assembly.metrics_service import (
        create_metrics_service as _create_metrics_service,
    )

    return _create_metrics_service(*args, **kwargs)


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
    if metrics_service_factory is None:
        service_factory = create_metrics_service
    else:
        service_factory = metrics_service_factory
    service = service_factory()
    result = service.start(
        port=settings.metrics_port,
        addr=settings.metrics_addr,
        fail_fast=resolve_metrics_fail_fast(settings),
        retry_count=obs.metrics_retry_count,
        retry_delay=obs.metrics_retry_delay,
    )
    return bool(result.success)
