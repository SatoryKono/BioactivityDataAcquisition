"""Reporting helpers for :mod:`bioetl.application.core.preflight.service`."""

from __future__ import annotations

__all__ = [
    "log_preflight_completed",
    "log_preflight_started",
    "raise_if_strict_blocking",
    "record_health_check_metrics",
    "record_preflight_metrics",
]

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import HealthReport, HealthStatus, PreflightReport

if TYPE_CHECKING:
    from bioetl.domain.config import PipelineConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, MetricsPort


class _PreflightLoggingHostProtocol(Protocol):
    _config: PipelineConfig
    _context: PipelineContext
    _logger: LoggerPort
    _metrics: MetricsPort


def record_health_check_metrics(
    host: _PreflightLoggingHostProtocol,
    report: HealthReport,
    duration: float,
) -> None:
    """Record health-check metrics per observability contract."""
    pipeline = host._config.pipeline_name

    for result in report.results:
        passed = 1.0 if result.status == HealthStatus.HEALTHY else 0.0
        host._metrics.set_gauge(
            "pipeline_health_check_passed",
            passed,
            {"pipeline": pipeline, "component": result.component},
        )

    validated = 1.0 if report.is_healthy else 0.0
    host._metrics.set_gauge(
        "infrastructure_validated",
        validated,
        {"pipeline": pipeline},
    )

    host._metrics.observe_histogram(
        "health_check_duration_seconds",
        duration,
        {"pipeline": pipeline},
    )


def record_preflight_metrics(
    host: _PreflightLoggingHostProtocol,
    report: PreflightReport,
) -> None:
    """Record preflight validation metrics."""
    pipeline = host._config.pipeline_name

    host._metrics.set_gauge(
        "preflight_medallion_policy_valid",
        1.0 if report.medallion_policy_valid else 0.0,
        {"pipeline": pipeline},
    )

    host._metrics.set_gauge(
        "preflight_config_errors_total",
        float(len(report.config_errors)),
        {"pipeline": pipeline},
    )


def log_preflight_started(
    host: _PreflightLoggingHostProtocol,
    *,
    strict_validation: bool,
) -> None:
    """Log preflight start event."""
    host._logger.info(
        "Starting preflight validation",
        stage="preflight",
        strict_mode=strict_validation,
    )


def log_preflight_completed(
    host: _PreflightLoggingHostProtocol,
    report: PreflightReport,
    *,
    is_healthy: bool,
) -> None:
    """Log preflight completion event."""
    host._logger.info(
        "Preflight validation completed",
        stage="preflight",
        medallion_policy_valid=report.medallion_policy_valid,
        config_error_count=len(report.config_errors),
        is_healthy=is_healthy,
        should_block=report.should_block_startup,
    )


def raise_if_strict_blocking(
    report: PreflightReport,
    *,
    strict_validation: bool,
) -> None:
    """Raise strict-mode preflight error when startup should be blocked."""
    if not (report.should_block_startup and strict_validation):
        return
    error_messages = [
        f"{error.field}: {error.actual} (expected: {error.expected})"
        for error in report.config_errors
    ]
    raise ValueError(
        "Preflight validation failed (strict mode): " + ", ".join(error_messages)
    )
