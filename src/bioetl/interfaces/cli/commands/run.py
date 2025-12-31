"""Run command for BioETL CLI.

Implements the main pipeline execution command using PipelineRunnerService.
"""

from __future__ import annotations

import asyncio
import sys

import click

from bioetl.application.services import (
    PipelineNotFoundError,
    RunOptions,
    RunStatus,
)
from bioetl.composition.entrypoints import get_pipeline_runner_service
from bioetl.interfaces.cli.commands.run_helpers import (
    get_runner_logger,
    handle_destructive_run_confirmation,
    show_cleanup_preview,
    validate_pipeline_name,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning


def _map_status_to_exit_code(status: RunStatus, error_type: str | None) -> ExitCode:
    """Map RunStatus to CLI exit code.

    Args:
        status: Run status from service.
        error_type: Exception type name if failed.

    Returns:
        Appropriate ExitCode for the status.
    """
    if status == RunStatus.SUCCESS:
        return ExitCode.OK
    if status == RunStatus.DRY_RUN:
        return ExitCode.OK
    if status == RunStatus.SHUTDOWN:
        return ExitCode.SIGINT
    # FAILED status - map based on error type
    if error_type:
        error_mapping = {
            "ValueError": ExitCode.CONFIG_ERROR,
            "FileNotFoundError": ExitCode.EX_NOINPUT,
            "ConfigValidationError": ExitCode.CONFIG_ERROR,
            "DataQualityError": ExitCode.DATA_QUALITY_ERROR,
            "DataQualityThresholdError": ExitCode.DATA_QUALITY_ERROR,
            "LockAcquisitionError": ExitCode.LOCK_ERROR,
            "LockLostError": ExitCode.LOCK_ERROR,
            "StorageError": ExitCode.STORAGE_ERROR,
            "NetworkError": ExitCode.NETWORK_ERROR,
            "RateLimitError": ExitCode.NETWORK_ERROR,
            "CircuitBreakerOpenError": ExitCode.NETWORK_ERROR,
        }
        return error_mapping.get(error_type, ExitCode.PIPELINE_ERROR)
    return ExitCode.PIPELINE_ERROR


async def _run_pipeline_async(
    pipeline: str,
    options: RunOptions,
) -> tuple[RunStatus, str | None, str | None]:
    """Run pipeline asynchronously via service.

    Args:
        pipeline: Pipeline name.
        options: Run options.

    Returns:
        Tuple of (status, error_message, error_type).
    """
    service = get_pipeline_runner_service()
    result = await service.run(pipeline, options=options)
    return result.status, result.error_message, result.error_type


def _echo_run_result(status: RunStatus, error_message: str | None) -> None:
    """Output run result message based on status."""
    status_handlers = {
        RunStatus.SUCCESS: lambda: echo_info("Pipeline completed successfully"),
        RunStatus.DRY_RUN: lambda: echo_info("Dry-run completed (no changes made)"),
        RunStatus.SHUTDOWN: lambda: echo_warning("Pipeline was gracefully shut down"),
        RunStatus.FAILED: lambda: echo_error(
            "Pipeline failed", error_message or "Unknown error"
        ),
    }
    handler = status_handlers.get(status)
    if handler:
        handler()


@click.command()
@click.option(
    "--pipeline",
    callback=validate_pipeline_name,
    required=True,
    help="Pipeline to run",
)
@click.option(
    "--run-type",
    type=click.Choice(["incremental", "backfill", "rebuild"]),
    default="incremental",
    help="Type of run",
)
@click.option("--resume", is_flag=True, help="Resume from last checkpoint")
@click.option("--limit", type=int, help="Maximum number of records to process")
@click.option(
    "--input-csv",
    type=click.Path(exists=True),
    help="Path to CSV file with filter IDs",
)
@click.option(
    "--filter-column",
    type=str,
    help="Column name in CSV containing filter IDs (default: 'id')",
)
@click.option(
    "--filter-field",
    type=str,
    help="API field name to filter by (default: 'molecule_chembl_id')",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview cleanup without execution (for rebuild/backfill)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt for rebuild/backfill",
)
@click.option(
    "--vacuum-after-run",
    is_flag=True,
    default=None,
    help="Run VACUUM on Delta tables after successful run (overrides YAML config)",
)
@click.option(
    "--vacuum-retention-days",
    type=int,
    default=None,
    help="Minimum age of files to remove during VACUUM (days, overrides YAML config)",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable DEBUG level logging for detailed output",
)
def run(
    pipeline: str,
    run_type: str,
    resume: bool,
    limit: int | None,
    input_csv: str | None,
    filter_column: str | None,
    filter_field: str | None,
    dry_run: bool,
    yes: bool,
    vacuum_after_run: bool | None,
    vacuum_retention_days: int | None,
    debug: bool,
) -> None:
    """Run an ETL pipeline."""
    # Handle confirmation for destructive operations (CLI responsibility)
    if not handle_destructive_run_confirmation(pipeline, run_type, dry_run, yes):
        return

    # Build options using application-layer RunOptions
    options = RunOptions(
        run_type=run_type,
        resume=resume,
        limit=limit,
        dry_run=dry_run,
        input_csv=input_csv,
        filter_column=filter_column,
        filter_field=filter_field,
        vacuum_after_run=vacuum_after_run if vacuum_after_run else None,
        vacuum_retention_days=vacuum_retention_days,
        log_level="DEBUG" if debug else "INFO",
    )

    # Run pipeline via service
    try:
        status, error_message, error_type = asyncio.run(
            _run_pipeline_async(pipeline, options)
        )
    except PipelineNotFoundError as e:
        echo_error("Pipeline not found", str(e))
        sys.exit(ExitCode.CONFIG_ERROR)
    except KeyboardInterrupt:
        echo_warning("Pipeline interrupted by user (Ctrl+C)")
        sys.exit(ExitCode.SIGINT)
    except Exception as e:
        echo_error("Unexpected error during pipeline execution", str(e))
        sys.exit(ExitCode.FAIL)

    # Map status to exit code and output result
    exit_code = _map_status_to_exit_code(status, error_type)
    _echo_run_result(status, error_message)
    sys.exit(exit_code)


# Re-export helpers for backward compatibility with tests
# These are imported by tests/unit/interfaces/test_cli.py
_get_runner_logger = get_runner_logger
_handle_destructive_run_confirmation = handle_destructive_run_confirmation
_preview_cleanup = show_cleanup_preview
