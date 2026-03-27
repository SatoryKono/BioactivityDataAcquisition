"""Metrics, logging, and assertion helpers for preflight health reports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.exceptions import InfrastructureError
from bioetl.domain.types import HealthReport, HealthStatus

if TYPE_CHECKING:
    from bioetl.domain.ports import HealthCheckResult, LoggerPort, MetricsPort
    from bioetl.domain.types import ComponentHealthResult

__all__ = [
    "assert_report_healthy",
    "log_health_report",
    "record_health_metrics",
    "record_probe_mode_fallback",
]


def record_health_metrics(
    *,
    metrics: MetricsPort | None,
    component: str,
    result: ComponentHealthResult,
    health_check_mode: str,
    metric_health_status: str,
    metric_health_mode_status: str,
    metric_health_latency: str,
    metric_health_mode_latency: str,
    health_result: HealthCheckResult | None = None,
) -> None:
    """Record status and latency metrics for one component result."""
    if metrics is None:
        return

    component_labels = {"component": component}
    metric_value = float(result.status.to_metric_value())

    metrics.set_gauge(
        metric_health_status,
        metric_value,
        component_labels,
    )
    metrics.set_gauge(
        metric_health_mode_status,
        metric_value,
        {"component": component, "mode": health_check_mode},
    )

    if health_result is None:
        return

    provider_labels = {"provider": health_result.provider}
    metrics.observe_histogram(
        metric_health_latency,
        health_result.latency_ms,
        provider_labels,
    )
    metrics.observe_histogram(
        metric_health_mode_latency,
        health_result.latency_ms,
        {"provider": health_result.provider, "mode": health_check_mode},
    )


def record_probe_mode_fallback(
    *,
    metrics: MetricsPort | None,
    pipeline_name: str,
    component: str,
    reason: str,
    metric_name: str,
) -> None:
    """Increment probe-mode fallback metrics when fallback behavior is used."""
    if metrics is None:
        return

    metrics.increment_counter(
        metric_name,
        1,
        {
            "pipeline": pipeline_name,
            "component": component,
            "reason": reason,
        },
    )


def log_health_report(
    *,
    logger: LoggerPort | None,
    report: HealthReport,
) -> None:
    """Emit one structured log entry per health component result."""
    if logger is None:
        return

    for result in report.results:
        log_extra: dict[str, str | float] = {
            "component": result.component,
            "status": result.status.value,
            "duration_seconds": round(result.duration_seconds, 4),
        }
        if result.error_message:
            log_extra["error"] = result.error_message

        if result.status == HealthStatus.HEALTHY:
            logger.info("Health check passed", **log_extra)
        elif result.status == HealthStatus.DEGRADED:
            logger.warning("Health check degraded", **log_extra)
        else:
            logger.error("Health check failed", **log_extra)


def assert_report_healthy(report: HealthReport) -> None:
    """Raise InfrastructureError when any component in report is UNHEALTHY."""
    failures = report.get_failures()
    if not failures:
        return

    failed_components = [failure.component for failure in failures]
    error_messages = [
        f"{failure.component}: {failure.error_message or 'check failed'}"
        for failure in failures
    ]
    raise InfrastructureError(
        f"Health check failed for: {', '.join(failed_components)}. "
        f"Details: {'; '.join(error_messages)}"
    )
