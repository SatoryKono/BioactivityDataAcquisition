"""Pipeline runner orchestration service."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, cast

from bioetl.application.core._runner_dependency_support import (
    PipelineRunnerDependencies,
)
from bioetl.application.core._runner_support import PipelineRunnerSupportMixin
from bioetl.application.core.lifecycle.shutdown import PipelineShutdownError
from bioetl.application.core.pipeline_span_lifecycle import (
    _TracingProvider,
    build_pipeline_span_attributes,
    start_current_span,
)
from bioetl.application.core.runner_flow import record_run_failed, record_run_started
from bioetl.application.services.debug_export_service import DebugExportResult
from bioetl.domain.exceptions.base import BioETLError
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
    from bioetl.application.core.pipeline_observability_service_protocols import (
        PipelineRunnerServicesProtocol,
    )
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, TracingPort

__all__ = ["PipelineRunner", "PipelineRunnerDependencies"]

_RUN_FAILURE_EXCEPTIONS = (
    BioETLError,
    AssertionError,
    AttributeError,
    KeyError,
    LookupError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


class PipelineRunner(PipelineRunnerSupportMixin):
    """Run the pipeline lifecycle while preserving stage and observer seams."""
    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineRunnerServicesProtocol,
        context: PipelineContext,
        dependencies: PipelineRunnerDependencies,
        *,
        pipeline: BasePipeline | None = None,
        tracer: TracingPort | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        """Initialize runner collaborators and enforce explicit tracer injection."""
        self._config = config
        self._runtime = runtime
        self._services = services
        self._context = context
        self._executor = dependencies.executor
        self._checkpoint_manager = dependencies.checkpoint_manager
        self._shutdown_signal = dependencies.shutdown_signal
        self._logger = logger or context.logger
        self._pipeline = pipeline
        if tracer is None:
            raise TypeError(
                "PipelineRunner requires explicit tracer injection. "
                "Build NoOpTracing in composition or test support when needed."
            )
        self._tracer = tracer
        self._lock_runtime_service = dependencies.lock_runtime_service
        self._preflight_service = dependencies.preflight
        self._postrun_service = dependencies.postrun
        self._lifecycle_service = dependencies.lifecycle_service
        self._observer = dependencies.observer
        self._run_ledger_service: RunLedgerService | None = None
    @property
    def logger(self) -> LoggerPort:
        return self._logger
    @property
    def shutdown_signal(self) -> ShutdownSignal:
        return self._shutdown_signal
    @property
    def run_id(self) -> str:
        return str(self._context.run_id)
    @property
    def manifest_id(self) -> str | None:
        manifest_id = getattr(self._context, "manifest_id", None)
        return None if manifest_id is None else str(manifest_id)
    @property
    def services(self) -> PipelineRunnerServicesProtocol:
        return self._services
    def attach_run_ledger_service(self, service: RunLedgerService) -> None:
        self._run_ledger_service = service
    @property
    def execution_metrics(self) -> dict[str, int]:
        gold_excluded = getattr(self._executor, "records_gold_excluded_by_contract", 0)
        if not isinstance(gold_excluded, int):
            gold_excluded = 0
        return {
            "records_fetched": int(self._executor.records_fetched),
            "records_bronze": int(self._executor.records_bronze),
            "records_silver": int(self._executor.records_silver),
            "records_gold": int(self._executor.records_gold),
            "records_gold_excluded_by_contract": gold_excluded,
            "records_quarantined": int(self._executor.records_quarantined),
            "records_filtered_out": int(self._executor.records_filtered_out),
        }
    def _debug_export_result(self) -> DebugExportResult | None:
        result = getattr(self._executor, "debug_export_result", None)
        return result if isinstance(result, DebugExportResult) else None
    @property
    def debug_export_uri(self) -> str | None:
        result = self._debug_export_result()
        return None if result is None else result.root_path
    @property
    def debug_export_hash(self) -> str | None:
        result = self._debug_export_result()
        return None if result is None else result.debug_export_hash
    @property
    def execution_diagnostics(self) -> JsonDict:
        diagnostics = getattr(self._executor, "execution_diagnostics", {})
        return diagnostics if isinstance(diagnostics, dict) else {}
    @contextmanager
    def _pipeline_span(self) -> Generator[Span, None, None]:
        with start_current_span(
            tracing=cast(_TracingProvider, self._tracer),
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
        """Execute the pipeline and always finalize shutdown/telemetry cleanup."""
        record_run_started(self)
        debug_export_status = "success"
        try:
            shutdown_recorded = await self._run_pipeline_lifecycle()
        except PipelineShutdownError:
            debug_export_status = "shutdown"
            self._record_terminal_shutdown()
            raise
        except _RUN_FAILURE_EXCEPTIONS as exc:
            debug_export_status = "failed"
            record_run_failed(self, exc)
            raise
        else:
            if not shutdown_recorded:
                self._record_successful_completion()
            else:
                debug_export_status = "shutdown"
        finally:
            await self._finalize_debug_export(debug_export_status)
            await self._cleanup_after_run()
    async def _run_pipeline_lifecycle(self) -> bool:
        shutdown_recorded = False
        with self._pipeline_span(), self._observer:
            try:
                async with self._services, self._lock_runtime_service:
                    await self._run_managed_pipeline()
            except PipelineShutdownError:
                self._record_terminal_shutdown()
                shutdown_recorded = True
                raise
            finally:
                self._observer.capture_execution_metrics(self.execution_metrics)
        return shutdown_recorded
    async def _finalize_debug_export(self, status: str) -> None:
        finalize = getattr(self._executor, "finalize_debug_export", None)
        if not callable(finalize):
            return
        try:
            from collections.abc import Awaitable, Callable
            finalize_fn = cast(Callable[..., Awaitable[object]], finalize)
            result = await finalize_fn(status=status, manifest_id=self.manifest_id)
        except _RUN_FAILURE_EXCEPTIONS as error:
            self._logger.warning(
                "debug_export_finalize_failed",
                error=str(error),
                error_type=type(error).__name__,
                run_id=str(self._context.run_id),
            )
            return
        if not isinstance(result, DebugExportResult):
            return
        if self._run_ledger_service is not None:
            self._run_ledger_service.record_artifact_published(
                layer="debug_export",
                artifact_path=result.root_path,
                artifact_content_hash=result.debug_export_hash,
                dataset_ref=f"debug_export:{self._config.pipeline_name}@{self.run_id}",
                details={
                    "manifest_path": result.manifest_path,
                    "debug_export_hash": result.debug_export_hash,
                },
            )
