"""Internal observability helpers for adapter health checks."""

from __future__ import annotations

import time

from bioetl.domain.ports import LoggerPort, MetricsPort
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.health_check_contract import HealthCheckContext


def start_health_check(
    *,
    provider_name: str,
    endpoint: str,
) -> HealthCheckContext:
    """Create a timed health-check context for observability."""
    return HealthCheckContext(
        start_time=time.monotonic(),
        provider=provider_name,
        endpoint=endpoint,
    )


def handle_health_check_result(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    ctx: HealthCheckContext,
    status: HealthStatus,
) -> None:
    """Record logs and counters for a completed health probe result."""
    elapsed = ctx.elapsed_seconds
    labels = {"provider": ctx.provider}
    if status == HealthStatus.HEALTHY:
        logger.debug(
            "health_check_passed",
            provider=ctx.provider,
            endpoint=ctx.endpoint,
            status=status.value,
            latency_seconds=elapsed,
        )
        if metrics is not None:
            metrics.increment_counter(
                "bioetl_health_check_success_total",
                1,
                labels,
            )
    elif status == HealthStatus.DEGRADED:
        logger.warning(
            "health_check_degraded",
            provider=ctx.provider,
            endpoint=ctx.endpoint,
            status=status.value,
            latency_seconds=elapsed,
        )
        if metrics is not None:
            metrics.increment_counter(
                "bioetl_health_check_degraded_total",
                1,
                labels,
            )
    else:
        logger.warning(
            "health_check_unhealthy",
            provider=ctx.provider,
            endpoint=ctx.endpoint,
            status=status.value,
            latency_seconds=elapsed,
        )
        if metrics is not None:
            metrics.increment_counter(
                "bioetl_health_check_failures_total",
                1,
                labels,
            )
    if metrics is not None:
        metrics.observe_histogram(
            "bioetl_health_check_latency_seconds",
            elapsed,
            labels,
        )


def handle_health_check_failure(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    ctx: HealthCheckContext,
    error: Exception,
) -> HealthStatus:
    """Record failure-side logs and metrics for a health probe."""
    elapsed = ctx.elapsed_seconds
    labels = {"provider": ctx.provider}
    logger.warning(
        "health_check_failed",
        provider=ctx.provider,
        endpoint=ctx.endpoint,
        error_type=type(error).__name__,
        error_message=str(error),
        latency_seconds=elapsed,
    )

    if metrics is not None:
        metrics.increment_counter(
            "bioetl_health_check_failures_total",
            1,
            labels,
        )
        metrics.observe_histogram(
            "bioetl_health_check_latency_seconds",
            elapsed,
            labels,
        )

    return HealthStatus.UNHEALTHY
