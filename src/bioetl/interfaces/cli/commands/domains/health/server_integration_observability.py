"""Metrics and observability helpers for the health server CLI surface."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, cast

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort


class _HealthObservabilitySettings(Protocol):
    @property
    def metrics_enabled(self) -> bool: ...

    @property
    def metrics_server_enabled(self) -> bool: ...

    @property
    def metrics_fail_fast(self) -> bool: ...

    @property
    def metrics_retry_count(self) -> int: ...

    @property
    def metrics_retry_delay(self) -> float: ...


class _HealthRuntimeSettings(Protocol):
    @property
    def metrics_port(self) -> int: ...

    @property
    def metrics_addr(self) -> str: ...

    @property
    def observability(self) -> _HealthObservabilitySettings: ...


def get_runtime_settings() -> _HealthRuntimeSettings:
    """Load runtime settings through the composition boundary."""
    from bioetl.composition.runtime_builders.config_access import get_settings as _impl

    return cast("_HealthRuntimeSettings", _impl())


def _start_metrics_server_via_interface(
    *,
    port: int,
    addr: str,
    fail_fast: bool,
    retry_count: int,
    retry_delay: float,
    logger: LoggerPort | None,
) -> bool:
    """Start the metrics server through the observability composition seam."""
    from bioetl.composition.observability_api import start_metrics_server as _impl

    starter = cast("Callable[..., bool]", _impl)
    return starter(
        port=port,
        addr=addr,
        fail_fast=fail_fast,
        retry_count=retry_count,
        retry_delay=retry_delay,
        logger=logger,
    )


start_metrics_server = _start_metrics_server_via_interface


def get_metrics_server_starter() -> Callable[..., bool]:
    """Expose the patchable metrics-server starter without direct call-site drift."""
    return start_metrics_server


def _start_health_observability(logger: LoggerPort | None = None) -> None:
    """Start the Prometheus metrics server for long-lived health mode."""
    settings = get_runtime_settings()
    if not (
        settings.observability.metrics_enabled
        and settings.observability.metrics_server_enabled
    ):
        if logger is not None:
            logger.info(
                "health_server_metrics_disabled",
                metrics_enabled=settings.observability.metrics_enabled,
                metrics_server_enabled=settings.observability.metrics_server_enabled,
            )
        return

    started = get_metrics_server_starter()(
        port=settings.metrics_port,
        addr=settings.metrics_addr,
        fail_fast=settings.observability.metrics_fail_fast,
        retry_count=settings.observability.metrics_retry_count,
        retry_delay=settings.observability.metrics_retry_delay,
        logger=logger,
    )
    if started:
        _rehydrate_current_metrics(logger=logger)
    if logger is None:
        return
    if started:
        logger.info(
            "health_server_metrics_ready",
            metrics_started=True,
            metrics_port=settings.metrics_port,
            metrics_addr=settings.metrics_addr,
        )
        return
    logger.warning(
        "health_server_metrics_not_started",
        metrics_started=False,
        metrics_port=settings.metrics_port,
        metrics_addr=settings.metrics_addr,
    )


def _rehydrate_current_metrics(*, logger: LoggerPort | None = None) -> None:
    """Seed scraped contract samples from durable run reports."""
    from bioetl.application.observability.current_metrics_rehydrate import (
        rehydrate_current_pipeline_run_metrics,
    )
    from bioetl.composition._services import get_health_server_dependencies

    try:
        deps = get_health_server_dependencies()
        result = rehydrate_current_pipeline_run_metrics(deps.metrics)
        _rehydrate_provider_health_gauges(deps)
    except (
        ImportError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        AttributeError,
    ) as exc:
        if logger is not None:
            logger.warning(
                "health_server_current_metrics_rehydrate_failed",
                error=str(exc),
            )
        return
    if logger is None:
        return
    if result.error:
        logger.warning(
            "health_server_current_metrics_rehydrate_failed",
            error=result.error,
        )
        return
    logger.info(
        "health_server_current_metrics_rehydrated",
        anchors=result.anchors,
        pipeline_runs_seeded=result.pipeline_runs_seeded,
        provider_universe_seeded=result.provider_universe_seeded,
        stage_series_seeded=result.stage_series_seeded,
    )


class _ProviderHealthDeps(Protocol):
    """Minimal typed view of health-server deps used for provider-health rehydrate."""

    metrics: MetricsPort


def _rehydrate_provider_health_gauges(deps: _ProviderHealthDeps) -> None:
    from bioetl.composition.factories.pipeline._preflight_health_monitor import (
        rehydrate_provider_health_gauges,
    )

    try:
        rehydrate_provider_health_gauges(deps.metrics)
    except (OSError, RuntimeError, TypeError, ValueError, AttributeError):
        return


__all__ = [
    "_rehydrate_current_metrics",
    "_start_health_observability",
    "get_metrics_server_starter",
    "get_runtime_settings",
    "start_metrics_server",
]
