"""Preflight Service for infrastructure validation.

Application Service that validates infrastructure health before pipeline execution.
Self-contained module with all validation logic integrated.

All helper components are internal:
- _HealthAggregator: handles health check aggregation
- _MedallionConfigValidator: handles medallion-specific validation
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from bioetl.domain.exceptions import InfrastructureError, PolicyViolationError
from bioetl.domain.medallion import Layer, MedallionPolicy, WriteMode, WriteModePolicy
from bioetl.domain.types import (
    ComponentHealthResult,
    ConfigValidationError,
    HealthReport,
    HealthStatus,
    PreflightReport,
    RunType,
)

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import HealthMonitorPort, LoggerPort, MetricsPort
    from bioetl.domain.ports.health_check import HealthCheckResult


# =============================================================================
# Private Helper: Health Aggregator
# =============================================================================


class _HealthAggregator:
    """Aggregates health checks for pipeline infrastructure components.

    Internal helper for PreflightService. Performs parallel health validation
    of storage and data source before pipeline execution.

    Integrates with ProviderHealthMonitor for:
    - Centralized health state tracking
    - P2 alerting on UNHEALTHY status
    - Adaptive client configuration based on health
    """

    METRIC_HEALTH_STATUS = "health_check_status"
    METRIC_HEALTH_DURATION = "health_check_duration_seconds"
    METRIC_HEALTH_LATENCY = "health_check_latency_ms"

    def __init__(
        self,
        metrics: MetricsPort | None = None,
        logger: LoggerPort | None = None,
        health_monitor: HealthMonitorPort | None = None,
    ) -> None:
        """Initialize _HealthAggregator.

        Args:
            metrics: Optional metrics port for recording health check metrics.
            logger: Optional logger for health check status reporting.
            health_monitor: Optional HealthMonitorPort for centralized
                health state tracking and alerting.

        """
        self._metrics = metrics
        self._logger = logger
        self._health_monitor = health_monitor

    async def check_all(self, services: PipelineServices) -> HealthReport:
        """Check health of all critical infrastructure components.

        Performs parallel health checks on:
        - Storage (Bronze/Silver/Gold layers)
        - Data source (external API connectivity)

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

    async def _check_storage(self, services: PipelineServices) -> ComponentHealthResult:
        """Check storage health."""
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

        Uses enhanced check_health() method when available for detailed
        metrics including latency.
        """
        component = "data_source"
        start_time = time.perf_counter()
        health_result: HealthCheckResult | None = None

        try:
            if hasattr(services.data_source, "check_health"):
                health_result = await services.data_source.check_health()
                status = health_result.status
                duration = time.perf_counter() - start_time

                if self._health_monitor is not None:
                    self._health_monitor.update_from_health_check_result(
                        health_result, self._logger
                    )

                result = ComponentHealthResult(
                    component=component,
                    status=status,
                    duration_seconds=duration,
                    error_message=health_result.last_error,
                )
            else:
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

        self._record_metrics(component, result, health_result)
        return result

    def _record_metrics(
        self,
        component: str,
        result: ComponentHealthResult,
        health_result: HealthCheckResult | None = None,
    ) -> None:
        """Record health check metrics."""
        if self._metrics is None:
            return

        labels = {"component": component}

        self._metrics.set_gauge(
            self.METRIC_HEALTH_STATUS,
            float(result.status.to_metric_value()),
            labels,
        )

        self._metrics.observe_histogram(
            self.METRIC_HEALTH_DURATION,
            result.duration_seconds,
            labels,
        )

        if health_result is not None:
            provider_labels = {"provider": health_result.provider}
            self._metrics.observe_histogram(
                self.METRIC_HEALTH_LATENCY,
                health_result.latency_ms,
                provider_labels,
            )

    def _log_report(self, report: HealthReport) -> None:
        """Log health check report."""
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


# =============================================================================
# Private Helper: Medallion Config Validator
# =============================================================================


class _MedallionConfigValidator:
    """Validates Medallion architecture configuration.

    Internal helper for PreflightService. Validates:
    - Silver and Gold layer formats
    - Path uniqueness across layers
    - MedallionPolicy consistency with RunType
    - Write modes against layer policies
    """

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggerPort,
    ) -> None:
        """Initialize medallion config validator.

        Args:
            config: Pipeline configuration.
            logger: Structured logger.

        """
        self._config = config
        self._logger = logger

    def validate_medallion_config(
        self,
        runtime: RuntimeConfig,
        bronze_path: str,
        silver_path: str,
        gold_path: str,
        silver_format: str | None = None,
        gold_format: str | None = None,
    ) -> list[ConfigValidationError]:
        """Validate Medallion architecture invariants.

        Args:
            runtime: Runtime configuration with run type.
            bronze_path: Base path for Bronze layer storage.
            silver_path: Base path for Silver layer storage.
            gold_path: Base path for Gold layer storage.
            silver_format: Format of Silver layer.
            gold_format: Format of Gold layer.

        Returns:
            List of ConfigValidationError objects. Empty list means validation passed.

        """
        errors: list[ConfigValidationError] = []

        errors.extend(self._validate_layer_formats(silver_format, gold_format))
        errors.extend(
            self._validate_path_uniqueness(bronze_path, silver_path, gold_path)
        )

        policy = MedallionPolicy.for_run_type(runtime.run_type)
        errors.extend(
            self._validate_medallion_policy_consistency(runtime.run_type, policy)
        )

        self._log_medallion_validation_result(errors, runtime)
        return errors

    def validate_write_modes(self) -> list[ConfigValidationError]:
        """Validate that config write modes are allowed by medallion policy.

        Returns:
            List of ConfigValidationError if write modes violate policy.

        """
        errors: list[ConfigValidationError] = []
        write_mode_policy = WriteModePolicy()

        # Validate Silver write mode
        silver_mode = self._config.write_mode
        try:
            write_mode_policy.validate(Layer.SILVER, WriteMode(silver_mode))
        except (PolicyViolationError, ValueError):
            allowed = WriteModePolicy.ALLOWED_MODES[Layer.SILVER]
            allowed_names = ", ".join(
                m.value for m in sorted(allowed, key=lambda x: x.value)
            )
            errors.append(
                ConfigValidationError(
                    field="write_mode",
                    expected=f"one of: {allowed_names}",
                    actual=silver_mode,
                    rule="RULES §2.1: Silver layer allowed modes",
                )
            )

        # Validate Gold write mode
        gold_mode = self._config.gold_write_mode
        effective_gold_mode = "merge" if gold_mode == "scd2" else gold_mode
        try:
            write_mode_policy.validate(Layer.GOLD, WriteMode(effective_gold_mode))
        except (PolicyViolationError, ValueError):
            allowed = WriteModePolicy.ALLOWED_MODES[Layer.GOLD]
            allowed_names = ", ".join(
                m.value for m in sorted(allowed, key=lambda x: x.value)
            )
            errors.append(
                ConfigValidationError(
                    field="gold_write_mode",
                    expected=f"one of: {allowed_names}, scd2",
                    actual=gold_mode,
                    rule="RULES §2.1: Gold layer allowed modes",
                )
            )

        # Log validation results
        if errors:
            self._logger.warning(
                "Write mode validation found issues",
                extra={
                    "error_count": len(errors),
                    "errors": [{"field": e.field, "rule": e.rule} for e in errors],
                },
            )
        else:
            self._logger.debug(
                "Write mode validation passed",
                extra={
                    "silver_mode": silver_mode,
                    "gold_mode": gold_mode,
                },
            )

        return errors

    def _validate_layer_formats(
        self, silver_format: str | None, gold_format: str | None
    ) -> list[ConfigValidationError]:
        """Validate Silver and Gold layer formats."""
        errors: list[ConfigValidationError] = []

        if silver_format is not None and silver_format != "delta":
            errors.append(
                ConfigValidationError(
                    field="sink.silver.format",
                    expected="delta",
                    actual=silver_format,
                    rule="RULES §2.1: Silver MUST use Delta Lake",
                )
            )

        if gold_format is not None and gold_format != "delta":
            errors.append(
                ConfigValidationError(
                    field="sink.gold.format",
                    expected="delta",
                    actual=gold_format,
                    rule="RULES §2.1: Gold MUST use Delta Lake",
                )
            )

        return errors

    def _validate_path_uniqueness(
        self, bronze_path: str, silver_path: str, gold_path: str
    ) -> list[ConfigValidationError]:
        """Validate that layer paths are unique."""
        errors: list[ConfigValidationError] = []
        paths = {bronze_path, silver_path, gold_path}

        if len(paths) >= 3:
            return errors

        if bronze_path == silver_path:
            errors.append(
                ConfigValidationError(
                    field="storage.paths",
                    expected="unique paths for each layer",
                    actual=f"bronze_path == silver_path ({bronze_path})",
                    rule="Medallion Architecture: layers MUST have distinct paths",
                )
            )
        if silver_path == gold_path:
            errors.append(
                ConfigValidationError(
                    field="storage.paths",
                    expected="unique paths for each layer",
                    actual=f"silver_path == gold_path ({silver_path})",
                    rule="Medallion Architecture: layers MUST have distinct paths",
                )
            )
        if bronze_path == gold_path:
            errors.append(
                ConfigValidationError(
                    field="storage.paths",
                    expected="unique paths for each layer",
                    actual=f"bronze_path == gold_path ({bronze_path})",
                    rule="Medallion Architecture: layers MUST have distinct paths",
                )
            )

        return errors

    def _validate_medallion_policy_consistency(
        self,
        run_type: RunType,
        policy: MedallionPolicy,
    ) -> list[ConfigValidationError]:
        """Validate that MedallionPolicy is consistent with RunType."""
        errors: list[ConfigValidationError] = []

        if run_type in (RunType.REBUILD, RunType.BACKFILL):
            if not policy.should_clear_silver:
                errors.append(
                    ConfigValidationError(
                        field="medallion_policy.should_clear_silver",
                        expected="True",
                        actual="False",
                        rule=f"RULES §2.1: {run_type.value} MUST clear Silver layer",
                    )
                )
            if not policy.should_clear_gold:
                errors.append(
                    ConfigValidationError(
                        field="medallion_policy.should_clear_gold",
                        expected="True",
                        actual="False",
                        rule=f"RULES §2.1: {run_type.value} MUST clear Gold layer",
                    )
                )
        elif run_type == RunType.INCREMENTAL:
            if policy.should_clear_silver:
                errors.append(
                    ConfigValidationError(
                        field="medallion_policy.should_clear_silver",
                        expected="False",
                        actual="True",
                        rule="RULES §2.1: INCREMENTAL MUST NOT clear Silver layer",
                    )
                )
            if policy.should_clear_gold:
                errors.append(
                    ConfigValidationError(
                        field="medallion_policy.should_clear_gold",
                        expected="False",
                        actual="True",
                        rule="RULES §2.1: INCREMENTAL MUST NOT clear Gold layer",
                    )
                )

        return errors

    def _log_medallion_validation_result(
        self, errors: list[ConfigValidationError], runtime: RuntimeConfig
    ) -> None:
        """Log medallion validation results."""
        if errors:
            self._logger.warning(
                "Medallion config validation found issues",
                extra={
                    "error_count": len(errors),
                    "errors": [{"field": e.field, "rule": e.rule} for e in errors],
                    "strict_mode": runtime.strict_validation,
                },
            )
        else:
            self._logger.debug(
                "Medallion config validation passed",
                extra={"run_type": runtime.run_type.value},
            )


# =============================================================================
# Main Service: PreflightService
# =============================================================================


class PreflightService:
    """Validates infrastructure health before pipeline execution.

    Self-contained service that performs all pre-flight validation:
    - Infrastructure health checks (storage, data source)
    - Medallion configuration validation
    - Write mode policy validation

    Attributes:
        _config: Pipeline configuration.
        _context: Pipeline execution context.
        _logger: Structured logger.
        _metrics: Metrics port for recording.

    """

    def __init__(
        self,
        config: PipelineConfig,
        context: PipelineContext,
        logger: LoggerPort,
        metrics: MetricsPort,
    ) -> None:
        """Initialize preflight service.

        Args:
            config: Pipeline configuration.
            context: Pipeline execution context.
            logger: Structured logger.
            metrics: Metrics port for recording health check metrics.

        """
        self._config = config
        self._context = context
        self._logger = logger
        self._metrics = metrics
        self._health_aggregator = _HealthAggregator(
            metrics=metrics,
            logger=logger,
        )
        self._medallion_validator = _MedallionConfigValidator(
            config=config,
            logger=logger,
        )

    async def validate_infrastructure(self, services: PipelineServices) -> HealthReport:
        """Validate infrastructure health before pipeline execution.

        Performs health checks on storage and data source components.
        Records metrics per Unified Observability Contract.

        Args:
            services: Pipeline services containing storage and data source.

        Returns:
            HealthReport with aggregated results.

        Raises:
            InfrastructureError: If critical components are unhealthy.

        """
        self._logger.info(
            "Validating infrastructure health",
            extra={"stage": "health_check"},
        )

        start_time = time.perf_counter()
        report = await self._health_aggregator.check_all(services)
        duration = time.perf_counter() - start_time

        self._record_health_check_metrics(report, duration)

        self._logger.info(
            "Infrastructure health check completed",
            extra={
                "stage": "health_check",
                "overall_status": report.overall_status.value,
                "is_healthy": report.is_healthy,
                "components_checked": len(report.results),
                "duration_seconds": round(duration, 4),
            },
        )

        self._health_aggregator.assert_healthy(report)
        return report

    def _record_health_check_metrics(
        self,
        report: Any,
        duration: float,
    ) -> None:
        """Record health-check metrics per Unified Observability Contract."""
        pipeline = self._config.pipeline_name
        run_id = str(self._context.run_id)

        for result in report.results:
            passed = 1.0 if result.status == HealthStatus.HEALTHY else 0.0
            self._metrics.set_gauge(
                "pipeline_health_check_passed",
                passed,
                {"pipeline": pipeline, "component": result.component},
            )

        validated = 1.0 if report.is_healthy else 0.0
        self._metrics.set_gauge(
            "infrastructure_validated",
            validated,
            {"pipeline": pipeline, "run_id": run_id},
        )

        self._metrics.observe_histogram(
            "health_check_duration_seconds",
            duration,
            {"pipeline": pipeline},
        )

    def validate_medallion_config(
        self,
        runtime: RuntimeConfig,
        bronze_path: str,
        silver_path: str,
        gold_path: str,
        silver_format: str | None = None,
        gold_format: str | None = None,
    ) -> list[ConfigValidationError]:
        """Validate Medallion architecture invariants before pipeline execution.

        Args:
            runtime: Runtime configuration with run type.
            bronze_path: Base path for Bronze layer storage.
            silver_path: Base path for Silver layer storage.
            gold_path: Base path for Gold layer storage.
            silver_format: Format of Silver layer.
            gold_format: Format of Gold layer.

        Returns:
            List of ConfigValidationError objects. Empty list means validation passed.

        """
        return self._medallion_validator.validate_medallion_config(
            runtime=runtime,
            bronze_path=bronze_path,
            silver_path=silver_path,
            gold_path=gold_path,
            silver_format=silver_format,
            gold_format=gold_format,
        )

    def validate_write_modes(self) -> list[ConfigValidationError]:
        """Validate that config write modes are allowed by medallion policy.

        Returns:
            List of ConfigValidationError if write modes violate policy.

        """
        return self._medallion_validator.validate_write_modes()

    async def validate_preflight(
        self,
        services: PipelineServices,
        runtime: RuntimeConfig,
        bronze_path: str,
        silver_path: str,
        gold_path: str,
        silver_format: str | None = None,
        gold_format: str | None = None,
    ) -> PreflightReport:
        """Execute complete preflight validation.

        Performs all preflight checks:
        1. Infrastructure health validation
        2. Medallion config validation
        3. Write mode policy validation

        Args:
            services: Pipeline services for health checks.
            runtime: Runtime configuration.
            bronze_path: Base path for Bronze layer storage.
            silver_path: Base path for Silver layer storage.
            gold_path: Base path for Gold layer storage.
            silver_format: Format of Silver layer.
            gold_format: Format of Gold layer.

        Returns:
            PreflightReport with aggregated validation results.

        Raises:
            InfrastructureError: If critical infrastructure is unhealthy.
            ValueError: If medallion policy is invalid and strict_validation
                is enabled.

        """
        self._logger.info(
            "Starting preflight validation",
            extra={"stage": "preflight", "strict_mode": runtime.strict_validation},
        )

        # 1. Validate infrastructure health
        health_report = await self.validate_infrastructure(services)

        # 2. Validate medallion config
        config_errors = self.validate_medallion_config(
            runtime=runtime,
            bronze_path=bronze_path,
            silver_path=silver_path,
            gold_path=gold_path,
            silver_format=silver_format,
            gold_format=gold_format,
        )

        # 3. Validate write modes against policy
        write_mode_errors = self.validate_write_modes()
        config_errors.extend(write_mode_errors)

        # Determine if medallion policy is valid
        medallion_policy_valid = len(config_errors) == 0

        # Create preflight report
        report = PreflightReport(
            health_report=health_report,
            medallion_policy_valid=medallion_policy_valid,
            config_errors=config_errors,
        )

        self._record_preflight_metrics(report)

        self._logger.info(
            "Preflight validation completed",
            extra={
                "stage": "preflight",
                "medallion_policy_valid": medallion_policy_valid,
                "config_error_count": len(config_errors),
                "is_healthy": health_report.is_healthy,
                "should_block": report.should_block_startup,
            },
        )

        if report.should_block_startup and runtime.strict_validation:
            error_messages = [
                f"{e.field}: {e.actual} (expected: {e.expected})" for e in config_errors
            ]
            raise ValueError(
                f"Preflight validation failed (strict mode): {', '.join(error_messages)}"
            )

        return report

    def _record_preflight_metrics(self, report: PreflightReport) -> None:
        """Record preflight validation metrics."""
        pipeline = self._config.pipeline_name
        run_id = str(self._context.run_id)

        self._metrics.set_gauge(
            "preflight_medallion_policy_valid",
            1.0 if report.medallion_policy_valid else 0.0,
            {"pipeline": pipeline, "run_id": run_id},
        )

        self._metrics.set_gauge(
            "preflight_config_errors_total",
            float(len(report.config_errors)),
            {"pipeline": pipeline, "run_id": run_id},
        )


__all__ = ["PreflightService"]
