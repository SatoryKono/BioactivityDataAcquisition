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


def _resolve_legacy_dependencies(
    legacy_kwargs: dict[str, object],
) -> PipelineRunnerDependencies:
    """Resolve legacy constructor kwargs into structured dependencies."""
    values = {
        "executor": legacy_kwargs.get("executor"),
        "checkpoint_manager": legacy_kwargs.get("checkpoint_manager"),
        "shutdown_signal": legacy_kwargs.get("shutdown_signal"),
        "lock_manager": legacy_kwargs.get("lock_manager"),
        "preflight": legacy_kwargs.get("preflight"),
        "postrun": legacy_kwargs.get("postrun"),
        "lifecycle_service": legacy_kwargs.get("lifecycle_service"),
        "observer": legacy_kwargs.get("observer"),
    }
    missing = [name for name, value in values.items() if value is None]
    if missing:
        raise AssertionError("Legacy constructor path requires all legacy parameters")
    return PipelineRunnerDependencies(
        executor=cast("BatchExecutor", values["executor"]),
        checkpoint_manager=cast(
            "CheckpointManagerService", values["checkpoint_manager"]
        ),
        lock_manager=cast("LockCoordinator", values["lock_manager"]),
        preflight=cast("PreflightService", values["preflight"]),
        postrun=cast("PostrunService", values["postrun"]),
        lifecycle_service=cast(
            "MedallionLifecycleService",
            values["lifecycle_service"],
        ),
        observer=cast("PipelineObserver", values["observer"]),
        shutdown_signal=cast("ShutdownSignal", values["shutdown_signal"]),
    )


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
            tracer: Tracing port. Build NoOpTracing in composition or tests when
                tracing is intentionally disabled.
            logger: Optional logger override; defaults to context.logger.
        """
        self._config = config
        self._runtime = runtime
        self._services = services
        self._context = context
        if dependencies is None:
            dependencies = _resolve_legacy_dependencies(legacy_kwargs)
        self._executor = dependencies.executor
        self._checkpoint_manager = dependencies.checkpoint_manager
        self._shutdown_signal = dependencies.shutdown_signal
        legacy_logger = cast("LoggerPort | None", legacy_kwargs.get("logger"))
        self._logger = logger or legacy_logger or context.logger
        self._pipeline = pipeline
        if tracer is None:
            raise TypeError(
                "PipelineRunner requires explicit tracer injection. "
                "Build NoOpTracing in composition or test support when needed."
            )
        self._tracer = tracer

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
        self._log_start()

        try:
            with self._pipeline_span(), self._observer:
                async with self._services, self._lock_manager:
                    await self._run_managed_pipeline()

                self._log_completion()
        finally:
            await self._postrun_service.cleanup(self._tracer)

    def _log_start(self) -> None:
        """Emit the pipeline start event."""
        self._logger.info(
            PipelineEvent.START,
            pipeline=self._config.pipeline_name,
            stage="startup",
            run_type=self._runtime.run_type.value,
        )

    def _log_completion(self) -> None:
        """Emit the pipeline completion event."""
        self._logger.debug(
            PipelineEvent.COMPLETE,
            records_fetched=self._executor.records_fetched,
        )

    async def _run_managed_pipeline(self) -> None:
        """Run the validated pipeline lifecycle within managed contexts."""
        await self._validate_infrastructure()
        await self._prepare_medallion_layers()
        await self._run_execution_cycle()

    async def _run_execution_cycle(self) -> None:
        """Execute extraction, postrun, and checkpoint finalization."""
        offset = await self._resolve_execution_offset()
        await self._execute_pipeline(offset=offset)
        await self._run_postrun_phase()
        await self._checkpoint_manager.delete_checkpoint()

    async def _resolve_execution_offset(self) -> int | None:
        """Resolve the executor start offset from runtime overrides or checkpoint."""
        if self._runtime.start_offset is not None:
            self._logger.info(
                "Using manual start offset",
                offset=self._runtime.start_offset,
            )
            return self._runtime.start_offset

        checkpoint_meta = await self._checkpoint_manager.load_checkpoint()
        return self._extract_checkpoint_offset(checkpoint_meta)

    def _extract_checkpoint_offset(
        self,
        checkpoint_meta: dict[str, object] | None,
    ) -> int | None:
        """Extract the persisted record offset from checkpoint metadata."""
        if checkpoint_meta is None:
            return None
        return cast("int | None", checkpoint_meta.get("records_processed"))

    async def _execute_pipeline(self, *, offset: int | None) -> None:
        """Execute the pipeline batch executor with resolved runtime inputs."""
        await self._executor.execute(
            limit=self._runtime.limit,
            query=self._runtime.query,
            offset=offset,
        )

    async def _run_postrun_phase(self) -> None:
        """Run the postrun workflow using the executor's resolved DQ context."""
        dq_context = self._executor.get_dq_context()
        await self._postrun_service.run(
            executor=self._executor,
            dq_context=dq_context,
        )

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

    def _check_data_quality(self) -> None:
        """Check data quality metrics and report anomalies."""
        self._postrun_service.run_dq_checks(self._executor)

    async def _run_vacuum_if_enabled(self) -> None:
        """Run VACUUM on Silver and Gold tables if enabled."""
        await self._postrun_service.run_vacuum_if_enabled()

    async def _cleanup(self) -> None:
        """Cleanup all resources including observability."""
        await self._postrun_service.cleanup(self._tracer)
