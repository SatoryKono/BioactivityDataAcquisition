"""Health aggregation helper for preflight infrastructure validation."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Literal

from bioetl.application.core.batch_runtime_failure_policy import OPERATION_ERRORS
from bioetl.application.core.preflight.health_aggregator_reporting import (
    assert_report_healthy,
    log_health_report,
    record_health_metrics,
    record_probe_mode_fallback,
)
from bioetl.application.core.preflight.health_aggregator_runtime import (
    build_component_result,
    build_data_source_exception_result,
    build_parallel_exception_result,
    normalize_data_source_error,
    normalize_data_source_status,
    resolve_probe_fallback_reason,
)
from bioetl.domain.types import ComponentHealthResult, HealthReport, HealthStatus

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.domain.ports import (
        HealthCheckResult,
        HealthMonitorPort,
        LoggerPort,
        MetricsPort,
    )

_HEALTH_CHECK_ERRORS = OPERATION_ERRORS


class HealthAggregator:
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
        """Check storage and data source health in parallel.

        Args:
            services: Pipeline service container providing storage and data source ports.

        Returns:
            HealthReport aggregating per-component health results.
        """
        results = await asyncio.gather(
            self._check_storage(services),
            self._check_data_source(services),
            return_exceptions=True,
        )

        component_results: list[ComponentHealthResult] = []
        for result in results:
            if isinstance(result, BaseException):
                component_results.append(build_parallel_exception_result(result))
            else:
                component_results.append(result)

        report = HealthReport(results=component_results)
        log_health_report(logger=self._logger, report=report)
        return report

    async def _check_storage(self, services: PipelineService) -> ComponentHealthResult:
        component = "storage"
        start_time = time.perf_counter()

        try:
            status = await services.storage.health_check()
            duration = time.perf_counter() - start_time
            result = build_component_result(
                component=component,
                status=status,
                duration_seconds=duration,
            )
        except _HEALTH_CHECK_ERRORS as exc:
            duration = time.perf_counter() - start_time
            result = build_component_result(
                component=component,
                status=HealthStatus.UNHEALTHY,
                duration_seconds=duration,
                error_message=str(exc),
            )

        record_health_metrics(
            metrics=self._metrics,
            component=component,
            result=result,
            health_check_mode=self._health_check_mode,
            metric_health_status=self.METRIC_HEALTH_STATUS,
            metric_health_mode_status=self.METRIC_HEALTH_MODE_STATUS,
            metric_health_latency=self.METRIC_HEALTH_LATENCY,
            metric_health_mode_latency=self.METRIC_HEALTH_MODE_LATENCY,
        )
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
                fallback_reason = resolve_probe_fallback_reason(
                    health_check_mode=self._health_check_mode,
                    status=status,
                )
                duration = time.perf_counter() - start_time

                if self._health_monitor is not None:
                    self._health_monitor.update_from_health_check_result(
                        health_result, self._logger
                    )

                result = build_component_result(
                    component=component,
                    status=normalize_data_source_status(
                        health_check_mode=self._health_check_mode,
                        status=status,
                    ),
                    duration_seconds=duration,
                    error_message=normalize_data_source_error(
                        health_check_mode=self._health_check_mode,
                        status=status,
                        error_message=health_result.last_error,
                    ),
                )
            else:
                status = await services.data_source.health_check()
                fallback_reason = resolve_probe_fallback_reason(
                    health_check_mode=self._health_check_mode,
                    status=status,
                )
                duration = time.perf_counter() - start_time
                result = build_component_result(
                    component=component,
                    status=normalize_data_source_status(
                        health_check_mode=self._health_check_mode,
                        status=status,
                    ),
                    duration_seconds=duration,
                    error_message=normalize_data_source_error(
                        health_check_mode=self._health_check_mode,
                        status=status,
                        error_message=None,
                    ),
                )
        except _HEALTH_CHECK_ERRORS as exc:
            duration = time.perf_counter() - start_time
            exception_message = str(exc)
            result = build_data_source_exception_result(
                health_check_mode=self._health_check_mode,
                duration_seconds=duration,
                exception_message=exception_message,
            )
            if self._health_check_mode == "probe":
                fallback_reason = "exception"

        record_health_metrics(
            metrics=self._metrics,
            component=component,
            result=result,
            health_check_mode=self._health_check_mode,
            metric_health_status=self.METRIC_HEALTH_STATUS,
            metric_health_mode_status=self.METRIC_HEALTH_MODE_STATUS,
            metric_health_latency=self.METRIC_HEALTH_LATENCY,
            metric_health_mode_latency=self.METRIC_HEALTH_MODE_LATENCY,
            health_result=health_result,
        )
        if fallback_reason is not None:
            record_probe_mode_fallback(
                metrics=self._metrics,
                pipeline_name=self._pipeline_name,
                component=component,
                reason=fallback_reason,
                metric_name=self.METRIC_PROBE_MODE_FALLBACK_TOTAL,
            )
        return result

    def assert_healthy(self, report: HealthReport) -> None:
        """Raise InfrastructureError when any component is UNHEALTHY.

        Args:
            report: HealthReport from a previous ``check_all()`` call.

        Raises:
            InfrastructureError: If any component in the report is UNHEALTHY.
        """
        assert_report_healthy(report)


# Backward-compatible alias kept for transitional imports.
_HealthAggregator = HealthAggregator

__all__ = ["HealthAggregator", "_HealthAggregator"]
