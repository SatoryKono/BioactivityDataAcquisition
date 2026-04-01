"""Execution lifecycle helpers for :mod:`bioetl.application.core.runner`."""

from __future__ import annotations

__all__ = [
    "execute_pipeline",
    "prepare_medallion_layers",
    "run_execution_cycle",
    "run_managed_pipeline",
    "run_postrun_phase",
    "validate_infrastructure",
]

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.events import ORDINARY_PIPELINE_STAGE_NAMES

if TYPE_CHECKING:
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointManagerService,
    )
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.application.core.postrun.service import PostrunService
    from bioetl.application.core.preflight.service import PreflightService
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig


_PREFLIGHT_STAGE_NAME = ORDINARY_PIPELINE_STAGE_NAMES[0]
_PREPARE_MEDALLION_LAYERS_STAGE_NAME = ORDINARY_PIPELINE_STAGE_NAMES[1]
_EXECUTE_PIPELINE_STAGE_NAME = ORDINARY_PIPELINE_STAGE_NAMES[2]
_POSTRUN_STAGE_NAME = ORDINARY_PIPELINE_STAGE_NAMES[3]
_CHECKPOINT_FINALIZE_STAGE_NAME = ORDINARY_PIPELINE_STAGE_NAMES[4]


class _PipelineRunnerExecutionHostProtocol(Protocol):
    _config: PipelineConfig
    _runtime: RuntimeConfig
    _services: PipelineService
    _executor: BatchExecutor
    _checkpoint_manager: CheckpointManagerService
    _preflight_service: PreflightService
    _postrun_service: PostrunService
    _lifecycle_service: MedallionLifecycleService

    async def _resolve_execution_offset(self) -> int | None: ...

    def _record_stage_started(self, stage: str) -> None: ...

    def _record_stage_completed(self, stage: str) -> None: ...


async def run_managed_pipeline(host: _PipelineRunnerExecutionHostProtocol) -> None:
    """Run the validated pipeline lifecycle within managed contexts."""
    host._record_stage_started(_PREFLIGHT_STAGE_NAME)
    await validate_infrastructure(host)
    host._record_stage_completed(_PREFLIGHT_STAGE_NAME)
    host._record_stage_started(_PREPARE_MEDALLION_LAYERS_STAGE_NAME)
    await prepare_medallion_layers(host)
    host._record_stage_completed(_PREPARE_MEDALLION_LAYERS_STAGE_NAME)
    await run_execution_cycle(host)


async def run_execution_cycle(host: _PipelineRunnerExecutionHostProtocol) -> None:
    """Execute extraction, postrun, and checkpoint finalization."""
    offset = await host._resolve_execution_offset()
    host._record_stage_started(_EXECUTE_PIPELINE_STAGE_NAME)
    await execute_pipeline(host, offset=offset)
    host._record_stage_completed(_EXECUTE_PIPELINE_STAGE_NAME)
    host._record_stage_started(_POSTRUN_STAGE_NAME)
    await run_postrun_phase(host)
    host._record_stage_completed(_POSTRUN_STAGE_NAME)
    host._record_stage_started(_CHECKPOINT_FINALIZE_STAGE_NAME)
    await host._checkpoint_manager.delete_checkpoint()
    host._record_stage_completed(_CHECKPOINT_FINALIZE_STAGE_NAME)


async def execute_pipeline(
    host: _PipelineRunnerExecutionHostProtocol,
    *,
    offset: int | None,
) -> None:
    """Execute the pipeline batch executor with resolved runtime inputs."""
    await host._executor.execute(
        limit=host._runtime.limit,
        query=host._runtime.query,
        offset=offset,
    )


async def run_postrun_phase(host: _PipelineRunnerExecutionHostProtocol) -> None:
    """Run the postrun workflow using the executor's resolved DQ context."""
    dq_context = host._executor.get_dq_context()
    await host._postrun_service.run(
        executor=host._executor,
        dq_context=dq_context,
    )


async def validate_infrastructure(host: _PipelineRunnerExecutionHostProtocol) -> None:
    """Validate infrastructure health before pipeline execution."""
    await host._preflight_service.validate_infrastructure(host._services)


async def prepare_medallion_layers(host: _PipelineRunnerExecutionHostProtocol) -> None:
    """Prepare medallion layers according to the runtime policy."""
    await host._lifecycle_service.prepare_for_run(
        config=host._config,
        runtime=host._runtime,
    )
