"""Presentation helpers for run command output."""

from __future__ import annotations

from bioetl.application.services import PipelineRunResult, RunResult
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning

__all__ = ["echo_run_result"]


def echo_run_result(result: RunResult) -> None:
    """Output run result message and execution counters."""
    short_run_id = result.run_id[:8] if len(result.run_id) > 8 else result.run_id

    if result.status == PipelineRunResult.SUCCESS:
        echo_info(f"Pipeline completed successfully (run_id: {short_run_id})")
        echo_info(f"  - Bronze records:      {result.records_fetched}")
        echo_info(f"  - Silver records:      {result.records_silver}")
        if result.records_gold > 0:
            echo_info(f"  - Gold records:        {result.records_gold}")
        if result.records_quarantined > 0:
            echo_warning(f"  - Quarantined (DQ):    {result.records_quarantined}")
        else:
            echo_info("  - Quarantined (DQ):    0")
        return

    if result.status == PipelineRunResult.DRY_RUN:
        echo_info(f"Dry-run completed (no changes made) (run_id: {short_run_id})")
        return

    if result.status == PipelineRunResult.SHUTDOWN:
        echo_warning(f"Pipeline was gracefully shut down (run_id: {short_run_id})")
        echo_info(f"  - Processed so far:    {result.records_fetched}")
        return

    if result.status == PipelineRunResult.FAILED:
        echo_error(
            f"Pipeline failed (run_id: {short_run_id})",
            result.error_message or "Unknown error",
        )
        echo_info(f"  - Processed before failure: {result.records_fetched}")
