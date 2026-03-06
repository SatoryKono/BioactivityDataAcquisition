"""Health aggregation helper for preflight infrastructure validation."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Literal

from bioetl.domain.exceptions import BioETLError, InfrastructureError
from bioetl.domain.types import ComponentHealthResult, HealthReport, HealthStatus

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.domain.ports import (
        HealthCheckResult,
        HealthMonitorPort,
        LoggerPort,
        MetricsPort,
    )

_HEALTH_CHECK_ERRORS = (
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


class _HealthAggregator:
    """Aggregates health checks for critical infrastructure components."""

    METRIC_HEALTH_STATUS = "health_check_status"
    METRIC_HEALTH_MODE_STATUS = "health_check_mode_status"
    METRIC_HEALTH_DURATION = "health_check_duration_seconds"
    METRIC_HEALTH_LATENCY = "health_check_latency_ms"
    METRIC_HEALTH_MODE_LATENCY = "health_check_mode_latency_ms"
    METRIC_PROBE_MODE_FALLBACK_TOTAL = "probe_mode_fallback_total"

    def __init__(
        self,
        metrics: MetricsPort | None = None,
        logger: LoggerPort | None = None,
        health_monitor: HealthMonitorPort | None = None,
        pipeline_name: str | None = None,
        health_check_mode: Literal["strict", "probe"] = "strict",
    ) -> None:
        if health_check_mode not in {"strict", "probe"}:
            raise ValueError(
                "health_check_mode must be 'strict' or 'probe', "
                f"got {health_check_mode!r}"
            )
        self._metrics = metrics
        self._logger = logger
        self._health_monitor = health_monitor
        self._pipeline_name = pipeline_name or "unknown"
        self._health_check_mode = health_check_mode

    async def check_all(self, services: PipelineService) -> HealthReport:
        """Check storage and data source health in parallel."""
        results = await asyncio.gather(
            self._check_storage(services),
            self._check_data_source(services),
            return_exceptions=True,
        )

        component_results: list[ComponentHealthResult] = []
        for result in results:
            if isinstance(result, BaseException):
                component_results.append(
                    ComponentHealthResult(
                        component="unknown",
                        status=HealthStatus.UNHEALTHY,
                        duration_seconds=0.0,
                        error_message=str(result),
                    )
                )
            else:
                component_results.append(result)

        report = HealthReport(results=component_results)
        self._log_report(report)
        return report

    async def _check_storage(self, services: PipelineService) -> ComponentHealthResult:
        component = "storage"
        start_time = time.perf_counter()

        try:
            status = await services.storage.health_check()
            duration = time.perf_counter() - start_time
            result = ComponentHealthResult(
                component=component,
                status=status,
                duration_seconds=duration,
            )
        except _HEALTH_CHECK_ERRORS as exc:
            duration = time.perf_counter() - start_time
            result = ComponentHealthResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                duration_seconds=duration,
                error_message=str(exc),
            )

        self._record_metrics(component, result)
        return result

    async def _check_data_source(
        self, services: PipelineService
    ) -> ComponentHealthResult:
        """Check data source health, preferring enhanced check_health API."""
        component = "data_source"
        start_time = time.perf_counter()
        health_result: HealthCheckResult | None = None
        fallback_reason: str | None = None

        try:
            if hasattr(services.data_source, "check_health"):
                health_result = await services.data_source.check_health()
                status = health_result.status
                fallback_reason = self._resolve_probe_fallback_reason(status)
                duration = time.perf_counter() - start_time

                if self._health_monitor is not None:
                    self._health_monitor.update_from_health_check_result(
                        health_result, self._logger
                    )

                result = ComponentHealthResult(
                    component=component,
                    status=self._normalize_data_source_status(status),
                    duration_seconds=duration,
                    error_message=self._normalize_data_source_error(
                        status=status,
                        error_message=health_result.last_error,
                    ),
                )
            else:
                status = await services.data_source.health_check()
                fallback_reason = self._resolve_probe_fallback_reason(status)
                duration = time.perf_counter() - start_time
                result = ComponentHealthResult(
                    component=component,
                    status=self._normalize_data_source_status(status),
                    duration_seconds=duration,
                    error_message=self._normalize_data_source_error(
                        status=status,
                        error_message=None,
                    ),
                )
        except _HEALTH_CHECK_ERRORS as exc:
            duration = time.perf_counter() - start_time
            exception_message = str(exc)
            result = ComponentHealthResult(
                component=component,
                status=(
                    HealthStatus.DEGRADED
                    if self._health_check_mode == "probe"
                    else HealthStatus.UNHEALTHY
                ),
                duration_seconds=duration,
                error_message=(
                    f"probe_mode_fallback: {exception_message}"
                    if self._health_check_mode == "probe"
                    else exception_message
                ),
            )
            if self._health_check_mode == "probe":
                fallback_reason = "exception"

        self._record_metrics(component, result, health_result)
        if fallback_reason is not None:
            self._record_probe_mode_fallback(
                component=component, reason=fallback_reason
            )
        return result

    def _normalize_data_source_status(self, status: HealthStatus) -> HealthStatus:
        """Downgrade data-source UNHEALTHY to DEGRADED in probe mode."""
        if self._health_check_mode == "probe" and status == HealthStatus.UNHEALTHY:
            return HealthStatus.DEGRADED
        return status

    def _normalize_data_source_error(
        self,
        *,
        status: HealthStatus,
        error_message: str | None,
    ) -> str | None:
        """Attach deterministic probe fallback marker when UNHEALTHY is downgraded."""
        if self._health_check_mode != "probe" or status != HealthStatus.UNHEALTHY:
            return error_message
        detail = error_message or "data_source reported UNHEALTHY in health probe"
        return f"probe_mode_fallback: {detail}"

    def _resolve_probe_fallback_reason(self, status: HealthStatus) -> str | None:
        if self._health_check_mode == "probe" and status == HealthStatus.UNHEALTHY:
            return "status_downgrade"
        return None

    def _record_metrics(
        self,
        component: str,
        result: ComponentHealthResult,
        health_result: HealthCheckResult | None = None,
    ) -> None:
        if self._metrics is None:
            return

        component_labels = {"component": component}

        self._metrics.set_gauge(
            self.METRIC_HEALTH_STATUS,
            float(result.status.to_metric_value()),
            component_labels,
        )
        self._metrics.set_gauge(
            self.METRIC_HEALTH_MODE_STATUS,
            float(result.status.to_metric_value()),
            {"component": component, "mode": self._health_check_mode},
        )

        if health_result is not None:
            provider_labels = {"provider": health_result.provider}
            self._metrics.observe_histogram(
                self.METRIC_HEALTH_LATENCY,
                health_result.latency_ms,
                provider_labels,
            )
            self._metrics.observe_histogram(
                self.METRIC_HEALTH_MODE_LATENCY,
                health_result.latency_ms,
                {
                    "provider": health_result.provider,
                    "mode": self._health_check_mode,
                },
            )

    def _record_probe_mode_fallback(self, *, component: str, reason: str) -> None:
        if self._metrics is None:
            return
        self._metrics.increment_counter(
            self.METRIC_PROBE_MODE_FALLBACK_TOTAL,
            1,
            {
                "pipeline": self._pipeline_name,
                "component": component,
                "reason": reason,
            },
        )

    def _log_report(self, report: HealthReport) -> None:
        if self._logger is None:
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
                self._logger.info("Health check passed", **log_extra)
            elif result.status == HealthStatus.DEGRADED:
                self._logger.warning("Health check degraded", **log_extra)
            else:
                self._logger.error("Health check failed", **log_extra)

    def assert_healthy(self, report: HealthReport) -> None:
        """Raise InfrastructureError when any component is UNHEALTHY."""
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
