"""Prefect tasks and flows for pipeline orchestration.

This module wraps the clean application layer with Prefect decorators.
The application layer remains framework-agnostic while this module
provides Prefect-specific integration.

Architecture:
    orchestration/tasks.py (Prefect) -> application/core/executor.py (Pure Python)
                                     -> application/core/orchestrator.py (Pure Python)
"""

from typing import TYPE_CHECKING

from prefect import flow, task

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.executor import PipelineExecutor
    from bioetl.domain.types import Watermark


@task(name="Execute Pipeline")
async def execute_pipeline_task(
    executor: "PipelineExecutor",
    watermark: "Watermark | None",
    limit: int | None,
) -> None:
    """Prefect task wrapper for pipeline execution.

    This task wraps the clean PipelineExecutor.execute() method
    with Prefect's task decorator for observability and retry support.

    Args:
        executor: The pipeline executor instance
        watermark: Optional watermark for incremental processing
        limit: Optional limit on number of records to process
    """
    await executor.execute(watermark=watermark, limit=limit)


@flow(
    name="Pipeline Flow",
    log_prints=True,
    validate_parameters=False,
)
async def run_pipeline_flow(pipeline: "BasePipeline") -> None:
    """Prefect flow wrapper for running a complete pipeline.

    This flow wraps the clean PipelineOrchestrator.run() method
    with Prefect's flow decorator for observability.

    Args:
        pipeline: The pipeline instance to run
    """
    await pipeline.orchestrator.run()
