"""Preflight Service for infrastructure validation.

Application Service that validates infrastructure health before pipeline execution.
Extracted from PipelineRunner to follow Single Responsibility Principle.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from bioetl.application.core.health_aggregator import HealthAggregator
from bioetl.domain.events import PipelineEvent
from bioetl.domain.medallion import MedallionPolicy
from bioetl.domain.types import (
    ConfigValidationError,
    HealthReport,
    HealthStatus,
    RunType,
)

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, MetricsPort


class PreflightService:
    """Validates infrastructure health before pipeline execution.

    Responsibilities:
    - Pre-flight health checks for storage and data source
    - Recording health check metrics
    - Fail-fast on infrastructure issues

    Attributes:
        _config: Pipeline configuration.
        _context: Pipeline execution context.
        _logger: Structured logger.
        _health_aggregator: Health check aggregator.
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
        self._health_aggregator = HealthAggregator(
            metrics=metrics,
            logger=logger,
        )

    async def validate_infrastructure(self, services: PipelineServices) -> HealthReport:
        """Validate infrastructure health before pipeline execution.

        Performs health checks on storage and data source components.
        Records metrics per Unified Observability Contract:
        - pipeline_health_check_passed: Per-component health status (1=passed, 0=failed)
        - infrastructure_validated: Overall validation status
        - health_check_duration_seconds: Total health check duration

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

        # Fail-fast if any critical component is unhealthy
        self._health_aggregator.assert_healthy(report)

        return report

    def _record_health_check_metrics(
        self,
        report: Any,
        duration: float,
    ) -> None:
        """Record health-check metrics per Unified Observability Contract.

        Records:
        - pipeline_health_check_passed: Per-component status (1=passed, 0=failed)
        - infrastructure_validated: Overall validation status
        - health_check_duration_seconds: Total duration

        Args:
            report: HealthReport from health aggregator.
            duration: Total health check duration in seconds.
        """
        pipeline = self._config.pipeline_name
        run_id = str(self._context.run_id)

        # Record per-component health check passed status
        for result in report.results:
            passed = 1.0 if result.status == HealthStatus.HEALTHY else 0.0
            self._metrics.set_gauge(
                PipelineEvent.HEALTH_CHECK_PASSED,
                passed,
                {"pipeline": pipeline, "component": result.component},
            )

        # Record overall infrastructure validation status
        validated = 1.0 if report.is_healthy else 0.0
        self._metrics.set_gauge(
            "infrastructure_validated",
            validated,
            {"pipeline": pipeline, "run_id": run_id},
        )

        # Record health check duration
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

        Проверяет соблюдение архитектурных инвариантов Medallion:
        - Silver format MUST be "delta" (RULES §4.1)
        - Gold format MUST be "delta" or "parquet" (RULES §4.1)
        - Bronze path != Silver path != Gold path (путь уникальности)
        - MedallionPolicy согласована с RunType

        Args:
            runtime: Runtime configuration with run type.
            bronze_path: Base path for Bronze layer storage.
            silver_path: Base path for Silver layer storage.
            gold_path: Base path for Gold layer storage.
            silver_format: Format of Silver layer (e.g., "delta", "parquet").
            gold_format: Format of Gold layer (e.g., "delta", "parquet").

        Returns:
            List of ConfigValidationError objects. Empty list means validation passed.

        Example:
            >>> errors = service.validate_medallion_config(
            ...     runtime, "/bronze", "/silver", "/gold",
            ...     silver_format="delta", gold_format="delta"
            ... )
            >>> if errors and runtime.strict_validation:
            ...     raise ValueError(f"Medallion invariant violations: {errors}")
        """
        errors: list[ConfigValidationError] = []

        # Validate Silver format
        if silver_format is not None and silver_format != "delta":
            errors.append(
                ConfigValidationError(
                    field="sink.silver.format",
                    expected="delta",
                    actual=silver_format,
                    rule="RULES §4.1: Silver MUST use Delta Lake",
                )
            )

        # Validate Gold format
        if gold_format is not None and gold_format not in ("delta", "parquet"):
            errors.append(
                ConfigValidationError(
                    field="sink.gold.format",
                    expected="delta or parquet",
                    actual=gold_format,
                    rule="RULES §4.1: Gold MUST use Delta Lake or Parquet",
                )
            )

        # Validate path uniqueness
        paths = {bronze_path, silver_path, gold_path}
        if len(paths) < 3:
            # Some paths are duplicated
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

        # Validate MedallionPolicy consistency with RunType
        policy = MedallionPolicy.for_run_type(runtime.run_type)
        errors.extend(
            self._validate_medallion_policy_consistency(runtime.run_type, policy)
        )

        # Log validation results
        if errors:
            self._logger.warning(
                "Medallion config validation found issues",
                extra={
                    "error_count": len(errors),
                    "errors": [
                        {"field": e.field, "rule": e.rule} for e in errors
                    ],
                    "strict_mode": runtime.strict_validation,
                },
            )
        else:
            self._logger.debug(
                "Medallion config validation passed",
                extra={"run_type": runtime.run_type.value},
            )

        return errors

    def _validate_medallion_policy_consistency(
        self,
        run_type: RunType,
        policy: MedallionPolicy,
    ) -> list[ConfigValidationError]:
        """Validate that MedallionPolicy is consistent with RunType.

        Проверяет соответствие политики очистки типу запуска:
        - REBUILD/BACKFILL: should_clear_silver and should_clear_gold MUST be True
        - INCREMENTAL: should NOT clear any layers

        Args:
            run_type: The type of pipeline run.
            policy: The MedallionPolicy derived from run_type.

        Returns:
            List of ConfigValidationError if inconsistencies found.
        """
        errors: list[ConfigValidationError] = []

        if run_type in (RunType.REBUILD, RunType.BACKFILL):
            # For REBUILD/BACKFILL, policy should clear both layers
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
            # For INCREMENTAL, policy should NOT clear any layers
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


__all__ = ["PreflightService"]
