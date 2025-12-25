"""Pipeline Runner.

Application Service that orchestrates pipeline execution lifecycle.
Coordinates locking, checkpointing, and execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.health_aggregator import HealthAggregator
from bioetl.application.core.lock_manager import LockManager
from bioetl.application.observability.observer import PipelineObserver

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.executor import PipelineExecutor
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.shutdown import ShutdownSignal
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, TracingPort


class PipelineRunner:
    """Manages the execution lifecycle of a pipeline.

    It coordinates application services like locking and checkpointing,
    but remains decoupled from the core business logic of the pipeline itself.
    """

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServices,
        context: PipelineContext,
        executor: PipelineExecutor,
        checkpoint_manager: CheckpointManager,
        shutdown_signal: ShutdownSignal,
        logger: LoggerPort,
        lifecycle_service: MedallionLifecycleService,
        pipeline: BasePipeline | None = None,
        tracer: TracingPort | None = None,
    ) -> None:
        """Initialize pipeline runner.

        Args:
            config: Pipeline configuration.
            runtime: Runtime configuration.
            services: Common pipeline services.
            context: Pipeline execution context.
            executor: Pipeline executor instance.
            checkpoint_manager: Checkpoint manager.
            shutdown_signal: Shutdown signal for graceful termination.
            logger: Structured logger.
            lifecycle_service: Medallion lifecycle service for data clearing.
            pipeline: Optional pipeline instance.
            tracer: Optional tracing port.

        """
        self._config = config
        self._runtime = runtime
        self._services = services
        self._context = context
        self._executor = executor
        self._checkpoint_manager = checkpoint_manager
        self.shutdown_signal = shutdown_signal
        self._logger = logger
        self._lifecycle_service = lifecycle_service
        self.pipeline = pipeline
        self._tracer = tracer

        # The runner is responsible for creating application services
        self._lock_manager = LockManager.create(
            lock_port=self._services.lock,
            run_id=self._context.run_id,
            provider=self._config.provider,
            entity_type=self._config.entity_type,
            run_type=self._runtime.run_type,
            lock_ttl=self._runtime.effective_lock_ttl,
            wait_for_lock=self._runtime.wait_for_lock,
            wait_timeout=self._runtime.lock_wait_timeout,
            heartbeat_interval=self._runtime.heartbeat_interval,
            logger=self._logger,
            shutdown_signal=self.shutdown_signal,
            checkpoint_manager=self._checkpoint_manager,  # Inject dependency
        )

        # Health aggregator for pre-flight infrastructure validation
        self._health_aggregator = HealthAggregator(
            metrics=self._services.metrics,
            logger=self._services.logger,
        )

    @property
    def logger(self) -> LoggerPort:
        """Get the logger instance."""
        return self._logger

    @property
    def services(self) -> PipelineServices:
        """Access injected services."""
        return self._services

    async def run(self) -> None:
        """Execute pipeline. Main entry point."""
        self._logger.info(
            f"Starting pipeline: {self._config.pipeline_name}",
            extra={"stage": "startup", "run_type": self._runtime.run_type.value},
        )

        # Initialize observer for automated metrics collection
        observer = PipelineObserver(
            pipeline_name=self._config.pipeline_name,
            run_id=self._context.run_id,
            run_type=self._runtime.run_type,
            metrics=self._services.metrics,
            logger=self._logger,
            tracer=self._tracer,
        )

        with observer:
            # Observer handles ShutdownSignal suppression and status recording
            async with self._services, self._lock_manager:
                # Pre-flight health check: validate infrastructure before execution
                await self._validate_infrastructure()

                # Clear data exports at the start of the run
                # to avoid appending to stale data from previous runs
                await self._clear_via_lifecycle()

                # Load checkpoint metadata (for logging purposes)
                await self._checkpoint_manager.load_checkpoint()
                await self._executor.execute(
                    limit=self._runtime.limit,
                    query=self._runtime.query,
                )

                # Check data quality after execution
                await self._check_data_quality()

                # Run VACUUM if enabled (Phase 1 refactoring)
                await self._run_vacuum_if_enabled()

                await self._checkpoint_manager.delete_checkpoint()

            # Add extra info to logs if needed, though observer handles success/failure logging
            self._logger.debug(
                "Pipeline execution finished",
                extra={"records_fetched": self._executor.records_fetched},
            )

    async def _validate_infrastructure(self) -> None:
        """Validate infrastructure health before pipeline execution.

        Performs health checks on storage and data source components.
        Raises InfrastructureError if critical components are unhealthy.
        """
        self._logger.info(
            "Validating infrastructure health",
            extra={"stage": "health_check"},
        )

        report = await self._health_aggregator.check_all(self._services)

        # Log overall health status
        self._logger.info(
            "Infrastructure health check completed",
            extra={
                "stage": "health_check",
                "overall_status": report.overall_status.value,
                "is_healthy": report.is_healthy,
                "components_checked": len(report.results),
            },
        )

        # Fail-fast if any critical component is unhealthy
        self._health_aggregator.assert_healthy(report)

    async def _clear_via_lifecycle(self) -> None:
        """Clear exports using MedallionLifecycleService (policy-based).

        Delegates clear decision to MedallionPolicy (Single Source of Truth).
        The policy determines which layers to clear based on run type:
        - REBUILD/BACKFILL: Clear both Silver and Gold
        - INCREMENTAL: Never clear (merge/upsert behavior)
        """
        from bioetl.domain.medallion import MedallionPolicy

        policy = MedallionPolicy.for_run_type(self._runtime.run_type)

        gold_table = (
            self._config.gold_table
            or f"{self._config.provider}.{self._config.entity_type}"
        )

        result = await self._lifecycle_service.clear(
            policy=policy,
            silver_table=self._config.silver_table,
            gold_table=gold_table,
            dry_run=self._runtime.dry_run,
        )

        self._logger.debug(
            "Medallion clear completed",
            extra={
                "run_type": self._runtime.run_type.value,
                "clear_policy": policy.clear_policy.value,
                "silver_cleared": result.silver_cleared,
                "gold_cleared": result.gold_cleared,
            },
        )

    def _collect_batch_metrics(self) -> dict[str, float]:
        """Collect batch metrics from executor."""
        total_records = max(1, self._executor.records_fetched)
        return {
            "record_count": float(self._executor.records_fetched),
            "bronze_count": float(self._executor.records_bronze),
            "silver_count": float(self._executor.records_silver),
            "gold_count": float(self._executor.records_gold),
            "quarantined_count": float(self._executor.records_quarantined),
            "error_rate": self._executor.records_quarantined / total_records,
            "silver_yield": self._executor.records_silver / total_records,
            "gold_yield": self._executor.records_gold / total_records,
        }

    def _process_anomaly(self, anomaly: Any) -> None:
        """Log and track a single anomaly."""
        self._logger.warning(
            "dq_anomaly_detected",
            anomaly_type=anomaly.anomaly_type.value,
            severity=anomaly.severity.value,
            metric=anomaly.metric_name,
            current_value=anomaly.current_value,
            baseline_mean=anomaly.baseline_mean,
            baseline_stddev=anomaly.baseline_stddev,
            z_score=anomaly.z_score,
            message=anomaly.message,
        )

        if self._services.metrics:
            self._services.metrics.increment_counter(
                "dq_anomaly_detected",
                1,
                {
                    "pipeline": self._config.pipeline_name,
                    "metric": anomaly.metric_name,
                    "severity": anomaly.severity.value,
                    "anomaly_type": anomaly.anomaly_type.value,
                },
            )

        if anomaly.severity.value == "critical":
            self._logger.error(
                "critical_dq_anomaly",
                metric=anomaly.metric_name,
                message=anomaly.message,
            )

    async def _check_data_quality(self) -> None:
        """Check data quality metrics and report anomalies."""
        if self._services.dq_monitor is None:
            return

        import time

        batch_metrics = self._collect_batch_metrics()

        start_time = time.monotonic()
        anomalies = self._services.dq_monitor.check_quality(batch_metrics)
        check_duration_ms = (time.monotonic() - start_time) * 1000

        if self._services.metrics:
            self._services.metrics.observe_histogram(
                "dq_check_duration_ms",
                check_duration_ms,
                {"pipeline": self._config.pipeline_name},
            )

        for anomaly in anomalies:
            self._process_anomaly(anomaly)

        self._services.dq_monitor.update_baseline_from_metrics(batch_metrics)

        if self._services.metrics and not any(
            a.severity.value == "critical" for a in anomalies
        ):
            for metric_name in batch_metrics:
                self._services.metrics.increment_counter(
                    "dq_baseline_updated",
                    1,
                    {"pipeline": self._config.pipeline_name, "metric": metric_name},
                )

    async def _run_vacuum_if_enabled(self) -> None:
        """Run VACUUM on Silver and Gold tables if enabled.

        Executes VACUUM using MedallionLifecycleService when:
        - runtime.vacuum_after_run is True
        - runtime.dry_run is False (no vacuum in dry-run mode)

        Uses runtime.vacuum_retention_days for retention policy (default: 7 days).
        """
        if not self._runtime.vacuum_after_run:
            return

        if self._runtime.dry_run:
            self._logger.info(
                "VACUUM skipped in dry-run mode",
                extra={"stage": "vacuum"},
            )
            return

        self._logger.info(
            "Starting VACUUM operation",
            extra={
                "stage": "vacuum",
                "retention_days": self._runtime.vacuum_retention_days,
            },
        )

        gold_table = (
            self._config.gold_table
            or f"{self._config.provider}.{self._config.entity_type}"
        )

        # VACUUM Silver table
        try:
            silver_files_removed = await self._lifecycle_service.vacuum(
                table=self._config.silver_table,
                retention_days=self._runtime.vacuum_retention_days,
                dry_run=False,
            )
            self._logger.info(
                "VACUUM completed for Silver table",
                extra={
                    "table": self._config.silver_table,
                    "files_removed": silver_files_removed,
                },
            )

            if self._services.metrics:
                self._services.metrics.increment_counter(
                    "vacuum_files_removed",
                    silver_files_removed,
                    {"pipeline": self._config.pipeline_name, "layer": "silver"},
                )
        except Exception as e:
            self._logger.warning(
                "VACUUM failed for Silver table",
                extra={"table": self._config.silver_table, "error": str(e)},
            )

        # VACUUM Gold table
        try:
            gold_files_removed = await self._lifecycle_service.vacuum(
                table=gold_table,
                retention_days=self._runtime.vacuum_retention_days,
                dry_run=False,
            )
            self._logger.info(
                "VACUUM completed for Gold table",
                extra={
                    "table": gold_table,
                    "files_removed": gold_files_removed,
                },
            )

            if self._services.metrics:
                self._services.metrics.increment_counter(
                    "vacuum_files_removed",
                    gold_files_removed,
                    {"pipeline": self._config.pipeline_name, "layer": "gold"},
                )
        except Exception as e:
            self._logger.warning(
                "VACUUM failed for Gold table",
                extra={"table": gold_table, "error": str(e)},
            )
