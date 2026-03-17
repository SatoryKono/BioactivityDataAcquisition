"""Pipeline Runner.

Application Service that orchestrates pipeline execution lifecycle.
Coordinates locking, checkpointing, and execution.

Delegates to specialized services (injected directly via DI):
- LockCoordinator: Distributed locking
- PreflightService: Infrastructure health validation
- PostrunService: DQ checks, VACUUM, cleanup
- MedallionLifecycleService: Medallion layer clearing and vacuum
- PipelineObserver: Observability wrapper for tracing, metrics, logging
"""

from __future__ import annotations

__all__ = ["PipelineRunner"]


from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from bioetl.domain.events import PipelineEvent
from bioetl.domain.ports import NoOpTracing

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointManagerService,
    )
    from bioetl.application.core.lifecycle.lock_manager import LockCoordinator
    from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.application.core.postrun.service import PostrunService
    from bioetl.application.core.preflight.service import PreflightService
    from bioetl.application.observability.observer import PipelineObserver
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, TracingPort


@dataclass(frozen=True, slots=True)
class PipelineRunnerDependencies:
    """Grouped collaborators for PipelineRunner."""

    executor: BatchExecutor
    checkpoint_manager: CheckpointManagerService
    lock_manager: LockCoordinator
    preflight: PreflightService
    postrun: PostrunService
    lifecycle_service: MedallionLifecycleService
    observer: PipelineObserver
    shutdown_signal: ShutdownSignal


class PipelineRunner:
    """Manages the execution lifecycle of a pipeline.

    It coordinates application services like locking and checkpointing,
    but remains decoupled from the core business logic of the pipeline itself.

    Delegates specialized operations to:
    - PreflightService: Pre-flight infrastructure validation
    - PostrunService: Post-run DQ checks, cleanup
    - MedallionLifecycleService: Pre-run clearing and post-run VACUUM
    """

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineService,
        context: PipelineContext,
        dependencies: PipelineRunnerDependencies | None = None,
        *,
        pipeline: BasePipeline | None = None,
        tracer: TracingPort | None = None,
        logger: LoggerPort | None = None,
        **legacy_kwargs: object,
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
            logger: Optional logger override; defaults to context.logger.
        """
        self._config = config
        self._runtime = runtime
        self._services = services
        self._context = context
        if dependencies is None:
            executor = cast("BatchExecutor | None", legacy_kwargs.get("executor"))
            checkpoint_manager = cast(
                "CheckpointManagerService | None",
                legacy_kwargs.get("checkpoint_manager"),
            )
            shutdown_signal = cast(
                "ShutdownSignal | None",
                legacy_kwargs.get("shutdown_signal"),
            )
            lock_manager = cast(
                "LockCoordinator | None",
                legacy_kwargs.get("lock_manager"),
            )
            preflight = cast(
                "PreflightService | None",
                legacy_kwargs.get("preflight"),
            )
            postrun = cast("PostrunService | None", legacy_kwargs.get("postrun"))
            lifecycle_service = cast(
                "MedallionLifecycleService | None",
                legacy_kwargs.get("lifecycle_service"),
            )
            observer = cast(
                "PipelineObserver | None",
                legacy_kwargs.get("observer"),
            )
            if (
                executor is None
                or checkpoint_manager is None
                or shutdown_signal is None
                or lock_manager is None
                or preflight is None
                or postrun is None
                or lifecycle_service is None
                or observer is None
            ):
                raise AssertionError(
                    "Legacy constructor path requires all legacy parameters"
                )
            dependencies = PipelineRunnerDependencies(
                executor=executor,
                checkpoint_manager=checkpoint_manager,
                lock_manager=lock_manager,
                preflight=preflight,
                postrun=postrun,
                lifecycle_service=lifecycle_service,
                observer=observer,
                shutdown_signal=shutdown_signal,
            )
        self._executor = dependencies.executor
        self._checkpoint_manager = dependencies.checkpoint_manager
        self._shutdown_signal = dependencies.shutdown_signal
        legacy_logger = cast("LoggerPort | None", legacy_kwargs.get("logger"))
        self._logger = logger or legacy_logger or context.logger
        self._pipeline = pipeline
        self._tracer: TracingPort = tracer if tracer is not None else NoOpTracing()

        # Services injected directly via DI (created in composition layer)
        self._lock_manager = dependencies.lock_manager
        self._preflight_service = dependencies.preflight
        self._postrun_service = dependencies.postrun
        self._lifecycle_service = dependencies.lifecycle_service
        self._observer = dependencies.observer

    @property
    def logger(self) -> LoggerPort:
        """Get the logger instance."""
        return self._logger

    @property
    def shutdown_signal(self) -> ShutdownSignal:
        """Shutdown signal for graceful termination (RunnablePort contract)."""
        return self._shutdown_signal

    @property
    def run_id(self) -> str:
        """Stable run identifier exposed by the runner contract."""
        return str(self._context.run_id)

    @property
    def services(self) -> PipelineService:
        """Access injected services."""
        return self._services

    @property
    def execution_metrics(self) -> dict[str, int]:
        """Return execution counters exposed by the concrete pipeline runner."""
        return {
            "records_fetched": int(self._executor.records_fetched),
            "records_bronze": int(self._executor.records_bronze),
            "records_silver": int(self._executor.records_silver),
            "records_gold": int(self._executor.records_gold),
            "records_quarantined": int(self._executor.records_quarantined),
        }

    @contextmanager
    def _pipeline_span(self) -> Generator[Span, None, None]:
        """Context manager for the top-level pipeline OTel span."""
        otel_tracer = self._tracer.get_tracer("bioetl.runner")
        with cast(
            "Span",
            otel_tracer.start_as_current_span(
                "pipeline.run",
                attributes={
                    "bioetl.pipeline": self._config.pipeline_name or "unknown",
                    "bioetl.provider": self._config.provider,
                    "bioetl.entity_type": self._config.entity_type,
                    "bioetl.run_type": self._runtime.run_type.value,
                    "bioetl.run_id": str(self._context.run_id),
                },
            ),
        ) as span:
            yield span

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
            with self._pipeline_span(), self._observer:
                async with self._services, self._lock_manager:
                    # Pre-flight: validate infrastructure
                    await self._preflight_service.validate_infrastructure(
                        self._services
                    )

                    # Lifecycle: prepare (clear based on run type policy)
                    await self._lifecycle_service.prepare_for_run(
                        config=self._config,
                        runtime=self._runtime,
                    )

                    # Execute pipeline (with manual offset or checkpoint-based resume)
                    offset: int | None
                    if self._runtime.start_offset is not None:
                        offset = self._runtime.start_offset
                        self._logger.info(
                            "Using manual start offset",
                            offset=offset,
                        )
                    else:
                        checkpoint_meta = (
                            await self._checkpoint_manager.load_checkpoint()
                        )
                        raw_offset: int | None = (
                            checkpoint_meta.get("records_processed")
                            if checkpoint_meta
                            else None
                        )
                        offset = raw_offset
                    await self._executor.execute(
                        limit=self._runtime.limit,
                        query=self._runtime.query,
                        offset=offset,
                    )

                    # Post-run: DQ checks, DQ reports, and VACUUM
                    dq_context = self._executor.get_dq_context()
                    await self._postrun_service.run(
                        executor=self._executor,
                        dq_context=dq_context,
                    )

                    await self._checkpoint_manager.delete_checkpoint()

                self._logger.debug(
                    PipelineEvent.COMPLETE,
                    records_fetched=self._executor.records_fetched,
                )
        finally:
            await self._postrun_service.cleanup(self._tracer)

    # Backward-compatible private methods (delegate to services)
    async def _validate_infrastructure(self) -> None:
        """Validate infrastructure health before pipeline execution."""
        await self._preflight_service.validate_infrastructure(self._services)

    async def _prepare_medallion_layers(self) -> None:
        """Prepare medallion layers (clear based on run type policy)."""
        await self._lifecycle_service.prepare_for_run(
            config=self._config,
            runtime=self._runtime,
        )

    async def _check_data_quality(self) -> None:
        """Check data quality metrics and report anomalies."""
        await self._postrun_service.run_dq_checks(self._executor)

    async def _run_vacuum_if_enabled(self) -> None:
        """Run VACUUM on Silver and Gold tables if enabled."""
        await self._postrun_service.run_vacuum_if_enabled()

    async def _cleanup(self) -> None:
        """Cleanup all resources including observability."""
        await self._postrun_service.cleanup(self._tracer)
