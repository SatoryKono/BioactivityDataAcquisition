"""Internal helper functions for the run-all CLI command."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.application.services import PipelineRunResult, RunOptions, RunResult
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning

if TYPE_CHECKING:
    from bioetl.application.services import RunResult


__all__ = [
    "create_run_all_options",
    "record_pipeline_failure",
    "record_pipeline_result",
]


class _BatchRunAccumulator(Protocol):
    """Minimal mutable contract needed for run-all batch result updates."""

    succeeded: int
    failed: int
    skipped: int
    results: list[RunResult]
    failed_pipelines: list[str]


def create_run_all_options(
    *,
    run_type: str,
    limit: int | None,
    dry_run: bool,
    debug: bool,
) -> RunOptions:
    """Build canonical RunOptions for the run-all command."""
    return RunOptions(
        run_type=run_type,
        limit=limit,
        dry_run=dry_run,
        log_level="DEBUG" if debug else "INFO",
    )


def record_pipeline_result(
    *,
    batch_result: _BatchRunAccumulator,
    pipeline: str,
    result: RunResult,
) -> bool:
    """Record one pipeline result and return whether the batch should stop."""
    batch_result.results.append(result)

    if result.status == PipelineRunResult.SUCCESS:
        batch_result.succeeded += 1
        echo_info(f"[OK] {pipeline}: completed successfully")
        return False

    if result.status == PipelineRunResult.DRY_RUN:
        batch_result.skipped += 1
        echo_info(f"[DRY] {pipeline}: dry-run (no changes)")
        return False

    if result.status == PipelineRunResult.SHUTDOWN:
        batch_result.skipped += 1
        echo_warning(f"[STOP] {pipeline}: gracefully shut down")
        return True

    if result.status == PipelineRunResult.FAILED:
        record_pipeline_failure(
            batch_result=batch_result,
            pipeline=pipeline,
            title=f"[FAIL] {pipeline}: failed",
            detail=result.error_message or "Unknown error",
        )

    return False


def record_pipeline_failure(
    *,
    batch_result: _BatchRunAccumulator,
    pipeline: str,
    title: str,
    detail: str,
) -> None:
    """Record a failed pipeline and emit a consistent error message."""
    batch_result.failed += 1
    batch_result.failed_pipelines.append(pipeline)
    echo_error(title, detail)
