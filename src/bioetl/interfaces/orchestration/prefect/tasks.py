"""Prefect tasks and flows for pipeline orchestration.

This module wraps the clean application layer with Prefect decorators.
The application layer remains framework-agnostic while this module
provides Prefect-specific integration.

Architecture:
    infrastructure/orchestration/prefect/tasks.py (Prefect) -> infrastructure/orchestration/runner.py (Pure Python)
                                                          -> application/core/executor.py (Pure Python)
"""

from typing import TYPE_CHECKING

from prefect import flow, task

if TYPE_CHECKING:
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.executor import PipelineExecutor
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.types import Watermark


# =============================================================================
# Executor Tasks
# =============================================================================


@task(name="Execute Pipeline")
async def execute_pipeline_task(
    executor: "PipelineExecutor",
    watermark: "Watermark | None",
    limit: int | None,
) -> None:
    """Prefect task wrapper for pipeline execution."""
    await executor.execute(watermark=watermark, limit=limit)


# =============================================================================
# Checkpoint Tasks
# =============================================================================


@task(name="Load Checkpoint", retries=2)
async def load_checkpoint_task(manager: "CheckpointManager") -> "Watermark | None":
    """Prefect task wrapper for loading checkpoints."""
    return await manager.load_checkpoint()


@task(name="Delete Checkpoint")
async def delete_checkpoint_task(manager: "CheckpointManager") -> None:
    """Prefect task wrapper for deleting checkpoints."""
    await manager.delete_checkpoint()


# =============================================================================
# Pipeline Flow
# =============================================================================


@flow(
    name="Pipeline Flow",
    log_prints=True,
    validate_parameters=False,
)
async def run_pipeline_flow(runner: "PipelineRunner") -> None:
    """Prefect flow wrapper for running a complete pipeline.

    This flow wraps the clean PipelineRunner.run() method
    with Prefect's flow decorator for observability.

    Args:
        runner: The pipeline runner instance to run.
    """
    await runner.run()
