"""Presentation helpers for run command output."""

from __future__ import annotations

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning

__all__ = ["echo_run_result"]


def echo_run_result(result: RunResult) -> None:
    """Output run result message and execution counters.

    Prints a human-readable summary of the pipeline run to stdout (or stderr
    for failures). Covers SUCCESS, DRY_RUN, SHUTDOWN, and FAILED statuses.

    Args:
        result: RunResult containing pipeline status, record counts, and run metadata.
    """
    short_run_id = result.run_id[:8] if len(result.run_id) > 8 else result.run_id
    if result.run_report_error:
        echo_warning(f"Run report unavailable: {result.run_report_error}")

    if result.status == PipelineRunResult.SUCCESS:
        echo_info(f"Pipeline completed successfully (run_id: {short_run_id})")
        echo_info(f"  - Bronze records:      {result.records_fetched}")
        echo_info(f"  - Silver records:      {result.records_silver}")
        if result.records_gold > 0:
            echo_info(f"  - Gold records:        {result.records_gold}")
        if result.records_filtered_out > 0:
            echo_info(f"  - Silver structural rejects: {result.records_filtered_out}")
        else:
            echo_info("  - Silver structural rejects: 0")
        if result.records_quarantined > 0:
            echo_info(f"  - Quarantined (DQ/contract): {result.records_quarantined}")
        else:
            echo_info("  - Quarantined (DQ/contract): 0")
        if result.records_gold_excluded_by_contract > 0:
            echo_info(
                f"  - Gold contract excludes: {result.records_gold_excluded_by_contract}"
            )
        if result.run_report_funnel:
            echo_info("  - Stage funnel:")
            for row in result.run_report_funnel:
                echo_info(
                    "    "
                    f"{row.stage_id}: in={row.records_in}, out={row.records_out}, "
                    f"removed={row.removed_total}, "
                    f"balance={row.balance_status.value}, "
                    f"tracking={row.tracking.value}"
                )
        if result.run_report_json_path:
            echo_info(f"  - Run report (JSON):    {result.run_report_json_path}")
        if result.run_report_markdown_path:
            echo_info(f"  - Run report (MD):      {result.run_report_markdown_path}")
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
