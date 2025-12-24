"""Pipeline Runner.

Application Service that orchestrates pipeline execution lifecycle.
Coordinates locking, checkpointing, and execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.lock_manager import LockManager
from bioetl.application.observability.observer import PipelineObserver

if TYPE_CHECKING:
    import structlog

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.executor import PipelineExecutor
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.shutdown import ShutdownSignal
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
    ) -> None:
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

    @property
    def logger(self) -> structlog.BoundLogger:
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
                # Clear data exports at the start of the run
                # to avoid appending to stale data from previous runs
                await self._clear_exports()

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

    async def _clear_exports(self) -> None:
        """Clear export files and Delta tables at the start of a pipeline run.

        Enforces Medallion architecture invariants:
        - Only clears data for rebuild/backfill runs
        - Incremental runs use merge/upsert and should NOT clear existing data

        This ensures data integrity and prevents accidental data loss.
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
