"""Finalize and archive helpers for PipelineRunnerService."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.evidence_location import (
    soft_invoke_evidence_location_verify,
)
from bioetl.application.services.execution._pipeline_runner_support import (
    build_pipeline_run_result,
    finalize_pipeline_run_report,
)
from bioetl.application.services.execution.pipeline_runner_models import (
    RunOptions,
    RunResult,
)
from bioetl.application.services.run_reports.control_plane_snapshot import (
    archive_run_completion,
    capture_run_completion,
)
from bioetl.domain.context import PipelineRunContext
from bioetl.domain.ports import RunReportStorePort
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_run_execution_service import (
        PipelineExecutionResult,
    )
    from bioetl.domain.ports import (
        ExecutionMetricsRunnerPort,
        LoggerPort,
        RunnerFactoryPort,
    )

__all__ = [
    "archive_pipeline_control_plane",
    "build_and_finalize_run_result",
    "create_pipeline_run_logger",
    "ensure_pipeline_registered",
    "finalize_pipeline_service_report",
]


def ensure_pipeline_registered(
    runner_factory: RunnerFactoryPort,
    pipeline_name: str,
    *,
    not_found_error: type[Exception],
) -> None:
    """Raise when the requested pipeline is not registered."""
    if runner_factory.contains(pipeline_name):
        return
    available = runner_factory.list_pipelines()
    raise not_found_error(pipeline_name, available)


def create_pipeline_run_logger(
    *,
    logger: LoggerPort,
    context: PipelineRunContext,
    options: RunOptions,
) -> LoggerPort:
    """Bind correlation fields and emit the run-start log line."""
    run_logger = logger.bind(**context.log_correlation_fields())
    run_logger.info(
        "Starting pipeline run",
        run_type=options.run_type,
        dry_run=options.dry_run,
        limit=options.limit,
    )
    return run_logger


def archive_pipeline_control_plane(
    archive_control_plane: Callable[[RunResult, RunOptions | None], None] | None,
    result: RunResult,
    options: RunOptions | None,
) -> None:
    """Publish control-plane archive evidence for a completed run."""
    archive_run_completion(archive_control_plane, result, options)


def finalize_pipeline_service_report(
    *,
    result: RunResult,
    options: RunOptions | None,
    report_root: Path | None,
    store: RunReportStorePort,
    capture_control_plane: Callable[[str, str, datetime], None] | None,
    archive_control_plane: Callable[[RunResult, RunOptions | None], None] | None,
    evidence_location_verify: Callable[[RunResult, RunOptions | None], None] | None,
) -> RunResult:
    """Capture control-plane evidence, persist the run report, then archive."""
    capture_run_completion(capture_control_plane, result, options)
    # RF-004: record Evidence Location observation BEFORE report snapshot.
    soft_invoke_evidence_location_verify(
        (
            None
            if evidence_location_verify is None
            else (lambda: evidence_location_verify(result, options))
        ),
        kind="pipeline",
        owner=str(result.pipeline_name),
        run_id=str(result.run_id),
    )
    finalized = finalize_pipeline_run_report(
        result=result,
        options=options,
        report_root=report_root,
        store=store,
    )
    archive_pipeline_control_plane(archive_control_plane, finalized, options)
    return finalized


def build_and_finalize_run_result(
    *,
    outcome: PipelineExecutionResult,
    runner: ExecutionMetricsRunnerPort,
    pipeline_name: str,
    run_id: RunID,
    run_type: str,
    started_at: datetime,
    options: RunOptions | None,
    store: RunReportStorePort,
    report_root: Path | None,
    capture_control_plane: Callable[[str, str, datetime], None] | None,
    archive_control_plane: Callable[[RunResult, RunOptions | None], None] | None,
    evidence_location_verify: Callable[[RunResult, RunOptions | None], None] | None,
) -> RunResult:
    """Convert execution outcome to public RunResult and finalize the report."""
    result = build_pipeline_run_result(
        outcome=outcome,
        runner=runner,
        pipeline_name=pipeline_name,
        run_id=run_id,
        run_type=run_type,
        started_at=started_at,
        options=options,
        write_report=False,
        store=store,
    )
    return finalize_pipeline_service_report(
        result=result,
        options=options,
        report_root=report_root,
        store=store,
        capture_control_plane=capture_control_plane,
        archive_control_plane=archive_control_plane,
        evidence_location_verify=evidence_location_verify,
    )
