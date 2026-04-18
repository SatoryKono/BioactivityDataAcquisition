"""Private support mixin for PipelineRunner delegated lifecycle helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
    from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


_METRICS_CLOSE_EXCEPTIONS = (
    AttributeError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


class PipelineRunnerSupportMixin:
    """Delegate thin lifecycle helpers away from the main runner module."""

    def _record_terminal_shutdown(self) -> None:
        record_run_shutdown(self)

    def _record_successful_completion(self) -> None:
        record_run_finished(self)

    async def _cleanup_after_run(self) -> None:
        try:
            await self._postrun_service.cleanup(self._tracer)
        finally:
            self._close_metrics()

    def _record_stage_started(self, stage: str) -> None:
        record_stage_started(self, stage)

    def _record_stage_completed(self, stage: str) -> None:
        record_stage_completed(self, stage)

    async def _run_managed_pipeline(self) -> None:
        await run_managed_pipeline(self)

    async def _run_execution_cycle(self) -> None:
        await run_execution_cycle(self)

    async def _resolve_execution_offset(self) -> int | None:
        return await resolve_execution_offset(self, load_runner_checkpoint)

    def _extract_checkpoint_offset(
        self,
        checkpoint_meta: CheckpointMetadata | dict[str, object] | None,
    ) -> int | None:
        return extract_checkpoint_offset(checkpoint_meta)

    async def _execute_pipeline(self, *, offset: int | None) -> None:
        await execute_pipeline(self, offset=offset)

    async def _run_postrun_phase(self) -> None:
        await run_postrun_phase(self)

    async def _validate_infrastructure(self) -> None:
        await validate_infrastructure(self)

    async def _prepare_medallion_layers(self) -> None:
        await prepare_medallion_layers(self)

    def _check_data_quality(self) -> None:
        self._postrun_service.run_dq_checks(self._executor)

    def _close_metrics(self) -> None:
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
