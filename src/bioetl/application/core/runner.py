"""Pipeline Runner.

Application Service that orchestrates pipeline execution lifecycle.
Coordinates locking, checkpointing, and execution.

Delegates to specialized handlers (Phase Handlers) for execution phases:
- PreflightHandler: Infrastructure validation
- InitializationHandler: Medallion preparation
- ExecutionHandler: Batch execution
- PostrunHandler: DQ, cleanup
- CleanupHandler: Final resource cleanup
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.handlers import (
    CleanupHandler,
    ExecutionHandler,
    InitializationHandler,
    PostrunHandler,
    PreflightHandler,
)
from bioetl.domain.events import PipelineEvent

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.lock_manager import LockManager
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.postrun_service import PostrunService
    from bioetl.application.core.preflight_service import PreflightService
    from bioetl.application.core.shutdown import ShutdownSignal
    from bioetl.application.observability.observer import PipelineObserver
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

    Delegates execution phases to dedicated handlers (Command pattern).
    """

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServices,
        context: PipelineContext,
        executor: BatchExecutor,
        checkpoint_manager: CheckpointManager,
        shutdown_signal: ShutdownSignal,
        logger: LoggerPort,
        lock_manager: LockManager,
        preflight: PreflightService,
        postrun: PostrunService,
        lifecycle_service: MedallionLifecycleService,
        observer: PipelineObserver,
        pipeline: BasePipeline | None = None,
        tracer: TracingPort | None = None,
    ) -> None:
        """Initialize pipeline runner.

        Args:
            config: Pipeline configuration.
            runtime: Runtime configuration.
            services: Common pipeline services.
            context: Pipeline execution context.
            executor: Batch executor instance (unified extraction + processing).
            checkpoint_manager: Checkpoint manager.
            shutdown_signal: Shutdown signal for graceful termination.
            logger: Structured logger.
            lock_manager: Distributed locking manager.
            preflight: Pre-flight infrastructure validation service.
            postrun: Post-run DQ checks service.
            lifecycle_service: Medallion lifecycle service for clearing and vacuum.
            observer: Pipeline observability wrapper for tracing, metrics, logging.
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
        self.pipeline = pipeline
        self._tracer = tracer

        # Services injected directly via DI (created in composition layer)
        self._lock_manager = lock_manager
        self._observer = observer

        # Initialize Phase Handlers
        self._preflight_handler = PreflightHandler(preflight, services)
        self._initialization_handler = InitializationHandler(lifecycle_service, config, runtime)
        self._execution_handler = ExecutionHandler(executor, checkpoint_manager, runtime)
        self._postrun_handler = PostrunHandler(postrun, executor, checkpoint_manager)
        self._cleanup_handler = CleanupHandler(postrun, tracer)

        # Keep references for backward compatibility accessors (if any)
        self._preflight_service = preflight
        self._postrun_service = postrun
        self._lifecycle_service = lifecycle_service

    @property
    def logger(self) -> LoggerPort:
        """Get the logger instance."""
        return self._logger

    @property
    def services(self) -> PipelineServices:
        """Access injected services."""
        return self._services

    async def run(self) -> None:
        """Execute pipeline. Main entry point.

        Implements graceful shutdown (O3):
        - Uses try/finally to ensure cleanup runs on all exit paths
        - Flushes tracer spans before shutdown
        - Handles tracer close errors without failing the pipeline
        """
        self._logger.info(
            PipelineEvent.START,
            pipeline=self._config.pipeline_name,
            stage="startup",
            run_type=self._runtime.run_type.value,
        )

        try:
            with self._observer:
                async with self._services, self._lock_manager:
                    # Pre-flight
                    await self._preflight_handler.handle()

                    # Lifecycle preparation
                    await self._initialization_handler.handle()

                    # Execute pipeline
                    await self._execution_handler.handle()

                    # Post-run
                    await self._postrun_handler.handle()

                self._logger.debug(
                    PipelineEvent.COMPLETE,
                    records_fetched=self._executor.records_fetched,
                )
        finally:
            await self._cleanup_handler.handle()

    # Backward-compatible private methods (delegate to handlers/services)
    async def _validate_infrastructure(self) -> None:
        """Validate infrastructure health before pipeline execution."""
        await self._preflight_handler.handle()

    async def _prepare_medallion_layers(self) -> None:
        """Prepare medallion layers (clear based on run type policy)."""
        await self._initialization_handler.handle()

    async def _check_data_quality(self) -> None:
        """Check data quality metrics and report anomalies."""
        await self._postrun_service.run_dq_checks(self._executor)

    async def _run_vacuum_if_enabled(self) -> None:
        """Run VACUUM on Silver and Gold tables if enabled."""
        await self._postrun_service.run_vacuum_if_enabled()

    async def _cleanup(self) -> None:
        """Cleanup all resources including observability."""
        await self._cleanup_handler.handle()
