# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
# Boundary object/payload typing residual at this module.
"""Private support mixin for PipelineRunner delegated lifecycle helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, cast
from bioetl.application.core.postrun._service_support import (
    PostrunServiceSupportHostProtocol,
)

from bioetl.application.core._runner_dependency_support import load_runner_checkpoint
from bioetl.application.core.runner_execution_flow import (
    execute_pipeline,
    prepare_medallion_layers,
    run_execution_cycle,
    run_managed_pipeline,
    run_postrun_phase,
    validate_infrastructure,
)
from bioetl.application.core.runner_flow import (
    extract_checkpoint_offset,
    record_run_finished,
    record_run_shutdown,
    record_stage_completed,
    record_stage_started,
    resolve_execution_offset,
)

if TYPE_CHECKING:
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.pipeline_service_protocols import (
        PipelineRunnerServicesProtocol,
    )
    from bioetl.application.core.postrun.service import PostrunService
    from bioetl.application.core.runner_execution_flow import (
        _PipelineRunnerExecutionHostProtocol,
    )
    from bioetl.application.core.runner_flow import _PipelineRunnerFlowHostProtocol
    from bioetl.domain.ports import LoggerPort, TracingPort
    from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

_METRICS_CLOSE_EXCEPTIONS = (
    AttributeError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


class _PipelineRunnerCleanupHostProtocol(Protocol):
    """Minimal host surface required for cleanup support methods."""

    _postrun_service: PostrunService = cast(Any, None)  # Any: host attr default (PD3)
    _tracer: TracingPort = cast(Any, None)  # Any: host attr default (PD3)
    _services: PipelineRunnerServicesProtocol = cast(
        Any, None
    )  # Any: host attr default (PD3)
    _logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD3)
    _executor: BatchExecutor = cast(Any, None)  # Any: host attr default (PD3)

    def _close_metrics(self) -> None: ...


class PipelineRunnerSupportMixin:
    """Delegate thin lifecycle helpers away from the main runner module."""

    _postrun_service: PostrunService = cast(Any, None)  # Any: host attr default (PD3)
    _tracer: TracingPort = cast(Any, None)  # Any: host attr default (PD3)
    _services: PipelineRunnerServicesProtocol = cast(
        Any, None
    )  # Any: host attr default (PD3)
    _logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD3)
    _executor: BatchExecutor = cast(Any, None)  # Any: host attr default (PD3)

    def _record_terminal_shutdown(self: _PipelineRunnerFlowHostProtocol) -> None:
        record_run_shutdown(self)

    def _record_successful_completion(self: _PipelineRunnerFlowHostProtocol) -> None:
        record_run_finished(self)

    async def _cleanup_after_run(self: _PipelineRunnerCleanupHostProtocol) -> None:
        try:
            await cast(Any, self._postrun_service).cleanup(self._tracer)
        finally:
            self._close_metrics()

    def _record_stage_started(
        self: _PipelineRunnerFlowHostProtocol,
        stage: str,
    ) -> None:
        record_stage_started(self, stage)

    def _record_stage_completed(
        self: _PipelineRunnerFlowHostProtocol,
        stage: str,
    ) -> None:
        record_stage_completed(self, stage)

    async def _run_managed_pipeline(
        self: _PipelineRunnerExecutionHostProtocol,
    ) -> None:
        await run_managed_pipeline(self)

    async def _run_execution_cycle(
        self: _PipelineRunnerExecutionHostProtocol,
    ) -> None:
        await run_execution_cycle(self)

    async def _resolve_execution_offset(
        self: _PipelineRunnerFlowHostProtocol,
    ) -> int | None:
        return await resolve_execution_offset(self, load_runner_checkpoint)

    def _extract_checkpoint_offset(
        self,
        checkpoint_meta: CheckpointMetadata | dict[str, object] | None,
    ) -> int | None:
        return extract_checkpoint_offset(checkpoint_meta)

    async def _execute_pipeline(
        self: _PipelineRunnerExecutionHostProtocol,
        *,
        offset: int | None,
    ) -> None:
        await execute_pipeline(self, offset=offset)

    async def _run_postrun_phase(
        self: _PipelineRunnerExecutionHostProtocol,
    ) -> None:
        await run_postrun_phase(self)

    async def _validate_infrastructure(
        self: _PipelineRunnerExecutionHostProtocol,
    ) -> None:
        await validate_infrastructure(self)

    async def _prepare_medallion_layers(
        self: _PipelineRunnerExecutionHostProtocol,
    ) -> None:
        await prepare_medallion_layers(self)

    def _check_data_quality(self: _PipelineRunnerCleanupHostProtocol) -> None:
        cast(Any, self._postrun_service).run_dq_checks(self._executor)  # pyright: ignore[reportArgumentType]

    def _close_metrics(self: _PipelineRunnerCleanupHostProtocol) -> None:
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
