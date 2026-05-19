"""Private helper functions for :mod:`pipeline_runner_service`."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunOptions,
    RunResult,
)

if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_run_execution_service import (
        PipelineExecutionResult,
    )
    from bioetl.domain.ports import ClockPort, ExecutionMetricsRunnerPort, LoggerPort
    from bioetl.domain.types import RunID


def build_dry_run_result(
    *,
    clock: ClockPort,
    pipeline_name: str,
    run_id: RunID,
    options: RunOptions,
    started_at: datetime,
    run_logger: LoggerPort,
) -> RunResult | None:
    """Build dry-run result when execution is intentionally skipped."""
    if not options.dry_run:
        return None
    run_logger.info("Dry-run mode: no execution performed")
    return RunResult(
        status=PipelineRunResult.DRY_RUN,
        pipeline_name=pipeline_name,
        run_id=str(run_id),
        run_type=options.run_type,
        started_at=started_at,
        completed_at=clock.now(),
    )


def build_pipeline_run_result(
    *,
    outcome: PipelineExecutionResult,
    runner: ExecutionMetricsRunnerPort,
    pipeline_name: str,
    run_id: RunID,
    run_type: str,
    started_at: datetime,
) -> RunResult:
    """Convert execution outcome to the public RunResult contract."""
    status = PipelineRunResult(outcome.status)
    metrics = outcome.metrics
    return RunResult(
        status=status,
        pipeline_name=pipeline_name,
        run_id=str(run_id),
        manifest_id=getattr(runner, "manifest_id", None),
        run_type=run_type,
        records_fetched=metrics.get("records_fetched", 0),
        records_bronze=metrics.get("records_bronze", 0),
        records_silver=metrics.get("records_silver", 0),
        records_gold=metrics.get("records_gold", 0),
        records_gold_excluded_by_contract=metrics.get(
            "records_gold_excluded_by_contract",
            0,
        ),
        records_quarantined=metrics.get("records_quarantined", 0),
        records_filtered_out=metrics.get("records_filtered_out", 0),
        started_at=started_at,
        completed_at=outcome.completed_at,
        error_message=outcome.error_message,
        error_type=outcome.error_type,
    )
