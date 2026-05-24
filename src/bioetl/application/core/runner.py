"""Pipeline runner orchestration service."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, cast

from bioetl.application.core._runner_dependency_support import (
    PipelineRunnerDependencies,
    resolve_runner_dependencies,
)
from bioetl.application.core._runner_support import PipelineRunnerSupportMixin
from bioetl.application.core.lifecycle.shutdown import PipelineShutdownError
from bioetl.application.core.runner_flow import (
    record_run_failed,
    record_run_started,
)
from bioetl.application.core.span_helpers import (
    _TracingProvider,
    build_pipeline_span_attributes,
    start_current_span,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointRuntimeService,
    )
    from bioetl.application.core.lifecycle.lock_runtime_service import (
        LockRuntimeService,
    )
    from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
    from bioetl.application.core.pipeline_observability_service_protocols import (
        PipelineRunnerServicesProtocol,
    )
    from bioetl.application.core.postrun.service import PostrunService
    from bioetl.application.core.preflight.service import PreflightService
    from bioetl.application.observability.observer import PipelineObserver
    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort, TracingPort

__all__ = ["PipelineRunner", "PipelineRunnerDependencies"]

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


class PipelineRunner(PipelineRunnerSupportMixin):
    """Run the pipeline lifecycle while preserving stage and observer seams."""

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineRunnerServicesProtocol,
        context: PipelineContext,
        dependencies: PipelineRunnerDependencies | None = None,
        *,
        pipeline: BasePipeline | None = None,
        tracer: TracingPort | None = None,
        logger: LoggerPort | None = None,
        executor: object | None = None,
        checkpoint_manager: object | None = None,
        shutdown_signal: object | None = None,
        lock_runtime_service: object | None = None,
        lock_manager: object | None = None,
        preflight: object | None = None,
        postrun: object | None = None,
        lifecycle_service: object | None = None,
        observer: object | None = None,
    ) -> None:
        """Initialize runner collaborators and enforce explicit tracer injection."""
        self._config = config
        self._runtime = runtime
        self._services = services
        self._context = context
        if dependencies is None:
            dependencies = resolve_runner_dependencies(
                executor=cast("BatchExecutor | None", executor),
                checkpoint_manager=cast(
                    "CheckpointRuntimeService | None",
                    checkpoint_manager,
                ),
                shutdown_signal=cast("ShutdownSignal | None", shutdown_signal),
                lock_runtime_service=cast(
                    "LockRuntimeService | None",
                    lock_runtime_service,
                ),
                lock_manager=cast("LockRuntimeService | None", lock_manager),
                preflight=cast("PreflightService | None", preflight),
                postrun=cast("PostrunService | None", postrun),
                lifecycle_service=cast(
                    "MedallionLifecycleService | None",
                    lifecycle_service,
                ),
                observer=cast("PipelineObserver | None", observer),
            )
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

        # Services injected directly via DI (created in composition layer)
        self._lock_runtime_service = dependencies.lock_runtime_service
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
    def services(self) -> PipelineRunnerServicesProtocol:
        """Access injected services."""
        return self._services

    def attach_run_ledger_service(self, service: RunLedgerService) -> None:
        """Attach a control-plane run-ledger collaborator from composition."""
        self._run_ledger_service = service

    @property
    def execution_metrics(self) -> dict[str, int]:
        """Return execution counters exposed by the concrete pipeline runner."""
        gold_excluded = getattr(
            self._executor,
            "records_gold_excluded_by_contract",
            0,
        )
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

    @property
    def execution_diagnostics(self) -> JsonDict:
        """Return bounded executor diagnostics for run-ledger projection."""
        diagnostics = getattr(self._executor, "execution_diagnostics", {})
        return diagnostics if isinstance(diagnostics, dict) else {}

    @contextmanager
    def _pipeline_span(self) -> Generator[Span, None, None]:
        """Context manager for the top-level pipeline OTel span."""
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
        """Execute pipeline. Main entry point.

        Implements graceful shutdown (O3):
        - Uses try/finally to ensure cleanup runs on all exit paths
        - Flushes tracer spans before shutdown
        - Handles tracer close errors without failing the pipeline
        """
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
                async with self._services, self._lock_runtime_service:
                    await self._run_managed_pipeline()
            except PipelineShutdownError:
                self._record_terminal_shutdown()
                shutdown_recorded = True
                raise
            finally:
                self._observer.capture_execution_metrics(self.execution_metrics)
        return shutdown_recorded
