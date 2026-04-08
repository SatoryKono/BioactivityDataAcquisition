"""Pipeline Runner.

Application Service that orchestrates pipeline execution lifecycle.
Coordinates locking, checkpointing, and execution.

Delegates to specialized services (injected directly via DI):
- LockCoordinator: Runtime locking
- PreflightService: Infrastructure health validation
- PostrunService: DQ checks, VACUUM, cleanup
- MedallionLifecycleService: Medallion layer clearing and vacuum
- PipelineObserver: Observability wrapper for tracing, metrics, logging
"""

from __future__ import annotations

__all__ = ["PipelineRunner"]


from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, cast

from bioetl.application.core._runner_dependency_support import (
    PipelineRunnerDependencies,
    load_runner_checkpoint,
    resolve_legacy_runner_dependencies,
)
from bioetl.application.core._span_helpers import (
    build_pipeline_span_attributes,
    start_current_span,
)
from bioetl.application.core.lifecycle.shutdown import PipelineShutdownError
from bioetl.application.core.runner_execution_flow import (
    execute_pipeline,
    prepare_medallion_layers,
    run_execution_cycle,
    run_managed_pipeline,
    run_postrun_phase,
    validate_infrastructure,
)
from bioetl.application.core.runner_flow import (
    emit_pipeline_completion,
    emit_pipeline_start,
    extract_checkpoint_offset,
    record_run_failed,
    record_run_finished,
    record_run_shutdown,
    record_run_started,
    record_stage_completed,
    record_stage_started,
    resolve_execution_offset,
)

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.application.services.run_ledger_service import RunLedgerService
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, TracingPort
    from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


_RUN_FAILURE_EXCEPTIONS = (
    AssertionError,
    AttributeError,
    KeyError,
    LookupError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)

_METRICS_CLOSE_EXCEPTIONS = (
    AttributeError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
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
            lock_manager: Runtime locking manager.
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
            dependencies = resolve_legacy_runner_dependencies(legacy_kwargs)
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
        self._run_ledger_service: RunLedgerService | None = None

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
    def manifest_id(self) -> str | None:
        """Control-plane manifest identifier linked to this run."""
        manifest_id = getattr(self._context, "manifest_id", None)
        return None if manifest_id is None else str(manifest_id)

    @property
    def services(self) -> PipelineService:
        """Access injected services."""
        return self._services

    def attach_run_ledger_service(self, service: RunLedgerService) -> None:
        """Attach a control-plane run-ledger collaborator from composition."""
        self._run_ledger_service = service

    @property
    def execution_metrics(self) -> dict[str, int]:
        """Return execution counters exposed by the concrete pipeline runner."""
        return {
            "records_fetched": int(self._executor.records_fetched),
            "records_bronze": int(self._executor.records_bronze),
            "records_silver": int(self._executor.records_silver),
            "records_gold": int(self._executor.records_gold),
            "records_quarantined": int(self._executor.records_quarantined),
            "records_filtered_out": int(self._executor.records_filtered_out),
        }

    @contextmanager
    def _pipeline_span(self) -> Generator[Span, None, None]:
        """Context manager for the top-level pipeline OTel span."""
        with start_current_span(
            tracing=self._tracer,
            tracer_name="bioetl.runner",
            span_name="pipeline.run",
            attributes=build_pipeline_span_attributes(
                config=self._config,
                runtime=self._runtime,
                context=self._context,
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
        emit_pipeline_start(self)
        record_run_started(self)
        try:
            shutdown_recorded = await self._run_pipeline_lifecycle()
        except PipelineShutdownError:
            self._record_terminal_shutdown()
            raise
        except _RUN_FAILURE_EXCEPTIONS as exc:
            record_run_failed(self, exc)
            raise
        else:
            if not shutdown_recorded:
                self._record_successful_completion()
        finally:
            await self._cleanup_after_run()

    async def _run_pipeline_lifecycle(self) -> bool:
        """Execute the observed pipeline lifecycle and report shutdown state."""
        shutdown_recorded = False
        with self._pipeline_span(), self._observer:
            try:
                async with self._services, self._lock_manager:
                    await self._run_managed_pipeline()
            except PipelineShutdownError:
                self._record_terminal_shutdown()
                shutdown_recorded = True
                raise
        return shutdown_recorded

    def _record_terminal_shutdown(self) -> None:
        """Append the canonical graceful-shutdown terminal ledger entry."""
        record_run_shutdown(self)

    def _record_successful_completion(self) -> None:
        """Emit canonical completion log + ledger entries for successful runs."""
        emit_pipeline_completion(self)
        record_run_finished(self)

    async def _cleanup_after_run(self) -> None:
        """Run the always-on cleanup sequence for one pipeline run."""
        try:
            await self._postrun_service.cleanup(self._tracer)
        finally:
            self._close_metrics()

    def _record_stage_started(self, stage: str) -> None:
        """Append stage_started ledger entry."""
        record_stage_started(self, stage)

    def _record_stage_completed(self, stage: str) -> None:
        """Append stage_completed ledger entry."""
        record_stage_completed(self, stage)

    async def _run_managed_pipeline(self) -> None:
        """Run the validated pipeline lifecycle within managed contexts."""
        await run_managed_pipeline(self)

    async def _run_execution_cycle(self) -> None:
        """Execute extraction, postrun, and checkpoint finalization."""
        await run_execution_cycle(self)

    async def _resolve_execution_offset(self) -> int | None:
        """Resolve the executor start offset from runtime overrides or checkpoint."""
        return await resolve_execution_offset(
            self,
            load_runner_checkpoint,
        )

    def _extract_checkpoint_offset(
        self,
        checkpoint_meta: CheckpointMetadata | dict[str, object] | None,
    ) -> int | None:
        """Extract the persisted record offset from checkpoint metadata."""
        return extract_checkpoint_offset(checkpoint_meta)

    async def _execute_pipeline(self, *, offset: int | None) -> None:
        """Execute the pipeline batch executor with resolved runtime inputs."""
        await execute_pipeline(self, offset=offset)

    async def _run_postrun_phase(self) -> None:
        """Run the postrun workflow using the executor's resolved DQ context."""
        await run_postrun_phase(self)

    # Backward-compatible private methods (delegate to services)
    async def _validate_infrastructure(self) -> None:
        """Validate infrastructure health before pipeline execution."""
        await validate_infrastructure(self)

    async def _prepare_medallion_layers(self) -> None:
        """Prepare medallion layers (clear based on run type policy)."""
        await prepare_medallion_layers(self)

    def _check_data_quality(self) -> None:
        """Check data quality metrics and report anomalies."""
        self._postrun_service.run_dq_checks(self._executor)

    def _close_metrics(self) -> None:
        """Close metrics after outer spans and observer teardown have completed."""
        try:
            self._services.metrics.close()
        except _METRICS_CLOSE_EXCEPTIONS as error:
            self._logger.warning(
                "Failed to close metrics",
                stage="cleanup",
                error=str(error),
                error_type=type(error).__name__,
                reason="metrics_close_failed",
            )
