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

    def _record_stage_completed(self, stage: str) -> None: ...


async def run_managed_pipeline(host: _PipelineRunnerExecutionHostProtocol) -> None:
    """Run the validated pipeline lifecycle within managed contexts."""
    await validate_infrastructure(host)
    host._record_stage_completed("preflight")
    await prepare_medallion_layers(host)
    host._record_stage_completed("prepare_medallion_layers")
    await run_execution_cycle(host)


async def run_execution_cycle(host: _PipelineRunnerExecutionHostProtocol) -> None:
    """Execute extraction, postrun, and checkpoint finalization."""
    offset = await host._resolve_execution_offset()
    await execute_pipeline(host, offset=offset)
    host._record_stage_completed("execute_pipeline")
    await run_postrun_phase(host)
    host._record_stage_completed("postrun")
    await host._checkpoint_manager.delete_checkpoint()
    host._record_stage_completed("checkpoint_finalize")


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
