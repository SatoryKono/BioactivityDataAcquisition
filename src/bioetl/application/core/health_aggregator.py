"""Health Aggregator for pre-flight infrastructure validation.

Validates infrastructure readiness before pipeline execution.
Implements parallel health checks for storage and data source components.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from bioetl.domain.exceptions import InfrastructureError
from bioetl.domain.types import ComponentHealthResult, HealthReport, HealthStatus

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.ports import LoggerPort, MetricsPort


class HealthAggregator:
    """Aggregates health checks for pipeline infrastructure components.

    Performs parallel health validation of storage and data source
    before pipeline execution. Records metrics for observability.

    Attributes:
        _metrics: Optional metrics port for recording health check metrics.
        _logger: Logger for health check status reporting.
    """

    # Metric names following Prometheus conventions
    METRIC_HEALTH_STATUS = "health_check_status"
    METRIC_HEALTH_DURATION = "health_check_duration_seconds"

    def __init__(
        self,
        metrics: MetricsPort | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        """Initialize HealthAggregator.

        Args:
            metrics: Optional metrics port for recording health check metrics.
            logger: Optional logger for health check status reporting.
        """
        self._metrics = metrics
        self._logger = logger

    async def check_all(self, services: PipelineServices) -> HealthReport:
        """Check health of all critical infrastructure components.

        Performs parallel health checks on:
        - Storage (Bronze/Silver/Gold layers)
        - Data source (external API connectivity)

        Records metrics:
        - health_check_status{component}: Gauge (0=UNHEALTHY, 1=DEGRADED, 2=HEALTHY)
        - health_check_duration_seconds{component}: Histogram of check duration

        Args:
            services: Pipeline services containing storage and data_source.

        Returns:
            HealthReport with aggregated results from all components.
        """
        results = await asyncio.gather(
            self._check_storage(services),
            self._check_data_source(services),
            return_exceptions=True,
        )

        component_results: list[ComponentHealthResult] = []
        for result in results:
            if isinstance(result, BaseException):
                # Convert exceptions to UNHEALTHY status
                component_results.append(
                    ComponentHealthResult(
                        component="unknown",
                        status=HealthStatus.UNHEALTHY,
                        duration_seconds=0.0,
                        error_message=str(result),
                    )
                )
            else:
                # result is ComponentHealthResult after exception check
                component_results.append(result)

        report = HealthReport(results=component_results)

        self._log_report(report)
        return report

    async def _check_storage(self, services: PipelineServices) -> ComponentHealthResult:
        """Check storage health.

        Args:
            services: Pipeline services containing storage.

        Returns:
            ComponentHealthResult for storage.
        """
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
        except Exception as e:
            duration = time.perf_counter() - start_time
            result = ComponentHealthResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                duration_seconds=duration,
                error_message=str(e),
            )

        self._record_metrics(component, result)
        return result

    async def _check_data_source(
        self, services: PipelineServices
    ) -> ComponentHealthResult:
        """Check data source health.

        Args:
            services: Pipeline services containing data_source.

        Returns:
            ComponentHealthResult for data source.
        """
        component = "data_source"
        start_time = time.perf_counter()

        try:
            status = await services.data_source.health_check()
            duration = time.perf_counter() - start_time

            result = ComponentHealthResult(
                component=component,
                status=status,
                duration_seconds=duration,
            )
        except Exception as e:
            duration = time.perf_counter() - start_time
            result = ComponentHealthResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                duration_seconds=duration,
                error_message=str(e),
            )

        self._record_metrics(component, result)
        return result

    def _record_metrics(self, component: str, result: ComponentHealthResult) -> None:
        """Record health check metrics.

        Args:
            component: Component name for metric labels.
            result: Health check result to record.
        """
        if self._metrics is None:
            return

        labels = {"component": component}

        # Record status as gauge (0=UNHEALTHY, 1=DEGRADED, 2=HEALTHY)
        self._metrics.set_gauge(
            self.METRIC_HEALTH_STATUS,
            float(result.status.to_metric_value()),
            labels,
        )

        # Record duration as histogram
        self._metrics.observe_histogram(
            self.METRIC_HEALTH_DURATION,
            result.duration_seconds,
            labels,
        )

    def _log_report(self, report: HealthReport) -> None:
        """Log health check report.

        Args:
            report: Health report to log.
        """
        if self._logger is None:
            return

        for result in report.results:
            log_extra = {
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
        """Assert that all critical components are healthy.

        Raises InfrastructureError if any component is UNHEALTHY.
        Used for fail-fast behavior before pipeline execution.

        Args:
            report: Health report to validate.

        Raises:
            InfrastructureError: If any component is UNHEALTHY.
        """
        failures = report.get_failures()
        if not failures:
            return

        failed_components = [f.component for f in failures]
        error_messages = [
            f"{f.component}: {f.error_message or 'check failed'}" for f in failures
        ]

        raise InfrastructureError(
            f"Health check failed for: {', '.join(failed_components)}. "
            f"Details: {'; '.join(error_messages)}"
        )


__all__ = ["HealthAggregator"]
