"""Pipeline Runner.

Application Service that orchestrates pipeline execution lifecycle.
Coordinates locking, checkpointing, and execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.health_aggregator import HealthAggregator
from bioetl.application.core.lock_manager import LockManager
from bioetl.application.observability.observer import PipelineObserver

if TYPE_CHECKING:
    import structlog

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.cleanup_service import CleanupService
    from bioetl.application.core.executor import PipelineExecutor
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.shutdown import ShutdownSignal
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import TracingPort


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
        logger: structlog.BoundLogger,
        pipeline: BasePipeline | None = None,
        tracer: TracingPort | None = None,
        lifecycle_service: MedallionLifecycleService | None = None,
        cleanup_service: CleanupService | None = None,
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
            pipeline: Optional pipeline instance.
            tracer: Optional tracing port.
            lifecycle_service: Optional medallion lifecycle service (M5).
            cleanup_service: Optional unified cleanup service.

        """
        self._config = config
        self._runtime = runtime
        self._services = services
        self._context = context
        self._executor = executor
        self._checkpoint_manager = checkpoint_manager
        self.shutdown_signal = shutdown_signal
        self._logger = logger
        self.pipeline = pipeline
        self._tracer = tracer
        self._lifecycle_service = lifecycle_service
        self._cleanup_service = cleanup_service

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
    def logger(self) -> structlog.BoundLogger:
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
        """Clear exports using lifecycle or cleanup service.

        Priority order:
        1. MedallionLifecycleService (policy-based clearing)
        2. CleanupService (unified cleanup service)
        3. Legacy inline logic (backward compatibility)
        """
        from bioetl.domain.types import RunType

        # Medallion invariant: only clear for destructive run types
        should_clear = self._runtime.run_type in (RunType.REBUILD, RunType.BACKFILL)

        if not should_clear:
            self._logger.debug(
                "Skipping clear for incremental run",
                extra={"run_type": self._runtime.run_type.value},
            )
            return

        # Use lifecycle service if available (policy-based clearing)
        if self._lifecycle_service is not None:
            await self._clear_via_lifecycle_service()
            return

        # Use cleanup service if available (unified cleanup)
        if self._cleanup_service is not None:
            await self._clear_via_cleanup_service()
            return

        # Fallback to legacy inline logic for backward compatibility
        await self._clear_exports_legacy()

    async def _clear_via_lifecycle_service(self) -> None:
        """Clear using MedallionLifecycleService (policy-based)."""
        from bioetl.domain.medallion import MedallionPolicy

        policy = MedallionPolicy.for_run_type(self._runtime.run_type)

        gold_table = (
            self._config.gold_table
            or f"{self._config.provider}.{self._config.entity_type}"
        )

        await self._lifecycle_service.clear(  # type: ignore[union-attr]
            policy=policy,
            silver_table=self._config.silver_table,
            gold_table=gold_table,
            dry_run=self._runtime.dry_run,
        )

    async def _clear_via_cleanup_service(self) -> None:
        """Clear using unified CleanupService."""
        gold_table = (
            self._config.gold_table
            or f"{self._config.provider}.{self._config.entity_type}"
        )

        await self._cleanup_service.execute(  # type: ignore[union-attr]
            silver_table=self._config.silver_table,
            gold_table=gold_table,
            dry_run=self._runtime.dry_run,
        )

    async def _clear_exports_legacy(self) -> None:
        """Clear export files and Delta tables (legacy fallback).

        This method is kept for backward compatibility when neither lifecycle
        nor cleanup service is injected. Will be deprecated in future versions.

        Enforces Medallion architecture invariants:
        - Only clears data for rebuild/backfill runs
        - Incremental runs use merge/upsert and should NOT clear existing data

        Note: This method has its own run type check for defense-in-depth,
        even though _clear_via_lifecycle() already checks the run type.
        """
        from bioetl.domain.types import RunType

        # Defense-in-depth: double-check run type
        if self._runtime.run_type not in (RunType.REBUILD, RunType.BACKFILL):
            return

        storage = self._services.storage
        silver_table = self._config.silver_table
        # Gold table defaults to {provider}.{entity_type} if not specified
        gold_table = (
            self._config.gold_table
            or f"{self._config.provider}.{self._config.entity_type}"
        )

        # Clear Silver and Gold layers using StoragePort methods (async)
        silver_cleared = await storage.clear_silver(
            silver_table, dry_run=self._runtime.dry_run
        )
        gold_cleared = await storage.clear_gold(
            gold_table, dry_run=self._runtime.dry_run
        )

        total_cleared = silver_cleared + gold_cleared

        if self._runtime.dry_run:
            self._logger.info(
                "DRY RUN: Would clear storage",
                extra={
                    "run_type": self._runtime.run_type.value,
                    "silver_table": silver_table,
                    "gold_table": gold_table,
                    "silver_would_clear": silver_cleared,
                    "gold_would_clear": gold_cleared,
                },
            )
        elif total_cleared > 0:
            self._logger.info(
                "Cleared storage for rebuild/backfill run",
                extra={
                    "run_type": self._runtime.run_type.value,
                    "silver_table": silver_table,
                    "gold_table": gold_table,
                    "silver_cleared": silver_cleared,
                    "gold_cleared": gold_cleared,
                },
            )
