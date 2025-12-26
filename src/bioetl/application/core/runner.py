"""Pipeline Runner.

Application Service that orchestrates pipeline execution lifecycle.
Coordinates locking, checkpointing, and execution.

Delegates to specialized services (injected via RunnerServices):
- LockManager: Distributed locking
- PreflightService: Infrastructure health validation
- PostrunService: DQ checks, VACUUM, cleanup
- LifecycleOrchestrator: Medallion layer clearing
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.observability.observer import PipelineObserver

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.executor import PipelineExecutor
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.shutdown import ShutdownSignal
    from bioetl.composition.factories.runner_services import RunnerServices
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, TracingPort


class PipelineRunner:
    """Manages the execution lifecycle of a pipeline.

    It coordinates application services like locking and checkpointing,
    but remains decoupled from the core business logic of the pipeline itself.

    Delegates specialized operations to:
    - PreflightService: Pre-flight infrastructure validation
    - PostrunService: Post-run DQ checks, VACUUM, cleanup
    - LifecycleOrchestrator: Medallion layer clear policies
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
        runner_services: RunnerServices,
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
            runner_services: Bundle of application services (lock_manager, preflight,
                postrun, lifecycle_orchestrator). Created in composition layer.
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

        # Injected application services (created in composition layer via RunnerServices)
        self._lock_manager = runner_services.lock_manager
        self._preflight_service = runner_services.preflight
        self._postrun_service = runner_services.postrun
        self._lifecycle_orchestrator = runner_services.lifecycle_orch

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
            f"Starting pipeline: {self._config.pipeline_name}",
            extra={"stage": "startup", "run_type": self._runtime.run_type.value},
        )

        observer = PipelineObserver(
            pipeline_name=self._config.pipeline_name,
            run_id=self._context.run_id,
            run_type=self._runtime.run_type,
            metrics=self._services.metrics,
            logger=self._logger,
            tracer=self._tracer,
        )

        try:
            with observer:
                async with self._services, self._lock_manager:
                    # Pre-flight: validate infrastructure
                    await self._preflight_service.validate_infrastructure(
                        self._services
                    )

                    # Lifecycle: clear data exports
                    await self._lifecycle_orchestrator.clear_for_run()

                    # Execute pipeline
                    await self._checkpoint_manager.load_checkpoint()
                    await self._executor.execute(
                        limit=self._runtime.limit,
                        query=self._runtime.query,
                    )

                    # Post-run: DQ checks and VACUUM
                    await self._postrun_service.run_dq_checks(self._executor)
                    await self._postrun_service.run_vacuum_if_enabled()

                    await self._checkpoint_manager.delete_checkpoint()

                self._logger.debug(
                    "Pipeline execution finished",
                    extra={"records_fetched": self._executor.records_fetched},
                )
        finally:
            await self._postrun_service.cleanup(self._tracer)

    # Backward-compatible private methods (delegate to services)
    async def _validate_infrastructure(self) -> None:
        """Validate infrastructure health before pipeline execution."""
        await self._preflight_service.validate_infrastructure(self._services)

    async def _clear_via_lifecycle(self) -> None:
        """Clear exports using MedallionLifecycleService (policy-based)."""
        await self._lifecycle_orchestrator.clear_for_run()

    async def _check_data_quality(self) -> None:
        """Check data quality metrics and report anomalies."""
        await self._postrun_service.run_dq_checks(self._executor)

    async def _run_vacuum_if_enabled(self) -> None:
        """Run VACUUM on Silver and Gold tables if enabled."""
        await self._postrun_service.run_vacuum_if_enabled()

    async def _cleanup(self) -> None:
        """Cleanup all resources including observability."""
        await self._postrun_service.cleanup(self._tracer)
