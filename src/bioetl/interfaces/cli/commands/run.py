"""Run command for BioETL CLI.

Implements the main pipeline execution command using PipelineRunnerService.
"""

from __future__ import annotations

import asyncio
import sys

import click

from bioetl.application.services import (
    PipelineNotFoundError,
    PipelineRunResult,
    RunOptions,
    RunResult,
)
from bioetl.composition.entrypoints import (
    get_pipeline_runner_service,
    push_metrics_to_gateway,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.health_server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
    health_server_context,
)
from bioetl.interfaces.cli.commands.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.run_helpers import (
    get_runner_logger,
    handle_destructive_run_confirmation,
    show_cleanup_preview,
    validate_pipeline_name,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error, echo_info, echo_warning


def validate_options(start_offset: int | None, run_type: str, resume: bool) -> None:
    """Validate --start-offset constraints; sys.exit on error."""
    if start_offset is None:
        return
    if start_offset < 0:
        echo_error("--start-offset must be non-negative")
        sys.exit(ExitCode.CONFIG_ERROR)
    if run_type != "incremental":
        echo_error("--start-offset requires --run-type=incremental")
        sys.exit(ExitCode.CONFIG_ERROR)
    if resume:
        echo_error("--start-offset and --resume cannot be used together")
        sys.exit(ExitCode.CONFIG_ERROR)


def build_run_options(
    run_type: str,
    resume: bool,
    start_offset: int | None,
    limit: int | None,
    input_csv: str | None,
    filter_column: str | None,
    filter_field: str | None,
    dry_run: bool,
    vacuum_after_run: bool | None,
    vacuum_retention_days: int | None,
    debug: bool,
    use_cached_bronze: bool,
    cached_bronze_date: str | None,
    cached_bronze_path: str | None,
) -> RunOptions:
    """Build RunOptions from CLI parameters."""
    return RunOptions(
        run_type=run_type,
        resume=resume,
        start_offset=start_offset,
        limit=limit,
        dry_run=dry_run,
        input_csv=input_csv,
        filter_column=filter_column,
        filter_field=filter_field,
        vacuum_after_run=vacuum_after_run if vacuum_after_run else None,
        vacuum_retention_days=vacuum_retention_days,
        log_level="DEBUG" if debug else "INFO",
        use_cached_bronze=use_cached_bronze,
        cached_bronze_path=cached_bronze_path,
        cached_bronze_date=cached_bronze_date,
    )


def execute_run(
    pipeline: str,
    options: RunOptions,
    health_server: bool,
    health_port: int,
) -> RunResult:
    """Execute run and always flush metrics at command boundary."""
    coro = _run_pipeline_async(
        pipeline,
        options,
        health_server_enabled=health_server,
        health_port=health_port,
    )
    try:
        return asyncio.run(coro)
    finally:
        push_metrics_to_gateway(pipeline_name=pipeline)
        if getattr(coro, "cr_frame", None) is not None:
            coro.close()


def handle_cli_failure(
    exc: BaseException,
    *,
    pipeline: str,
    reason_code: str,
) -> None:
    """Handle CLI failures with consistent reason_code semantics."""
    if reason_code.startswith("CLI_CLEANUP_PREVIEW"):
        if isinstance(exc, BioETLError):
            echo_error(
                "Error previewing cleanup",
                (
                    f"{exc} "
                    f"(reason_code={reason_code}, pipeline={pipeline}, "
                    f"error_type={type(exc).__name__})"
                ),
            )
            return
        echo_error(
            "Error previewing cleanup",
            (
                f"{exc} "
                f"(reason_code={reason_code}, pipeline={pipeline}, "
                f"error_type={type(exc).__name__})"
            ),
        )
        return

    if isinstance(exc, PipelineNotFoundError):
        echo_error("Pipeline not found", str(exc))
        sys.exit(ExitCode.CONFIG_ERROR)
    if isinstance(exc, BioETLError):
        echo_error(
            "Pipeline execution failed with domain error",
            (
                f"{exc} "
                f"(reason_code={reason_code}, pipeline={pipeline}, "
                f"error_type={type(exc).__name__})"
            ),
        )
        sys.exit(ExitCode.FAIL)
    if isinstance(exc, KeyboardInterrupt):
        echo_warning("Pipeline interrupted by user (Ctrl+C)")
        sys.exit(ExitCode.SIGINT)

    echo_error(
        "Unexpected error during pipeline execution",
        (
            f"{exc} "
            f"(reason_code={reason_code}, pipeline={pipeline}, "
            f"error_type={type(exc).__name__})"
        ),
    )
    sys.exit(ExitCode.FAIL)


def _map_status_to_exit_code(
    status: PipelineRunResult, error_type: str | None
) -> ExitCode:
    """Map PipelineRunResult to CLI exit code.

    Args:
        status: Run status from service.
        error_type: Exception type name if failed.

    Returns:
        Appropriate ExitCode for the status.
    """
    if status == PipelineRunResult.SUCCESS:
        return ExitCode.OK
    if status == PipelineRunResult.DRY_RUN:
        return ExitCode.OK
    if status == PipelineRunResult.SHUTDOWN:
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
    health_server_enabled: bool = True,
    health_port: int = DEFAULT_HEALTH_SERVER_PORT,
) -> RunResult:
    """Run pipeline asynchronously via service.

    Args:
        pipeline: Pipeline name.
        options: Run options.
        health_server_enabled: Whether to enable health server.
        health_port: Port for health server.

    Returns:
        RunResult object with status and metrics.
    """
    # Start metrics server if enabled (side-effect in entrypoint, not bootstrap)
    ensure_metrics_server_started()

    async with health_server_context(
        enabled=health_server_enabled,
        port=health_port,
    ):
        service = get_pipeline_runner_service()
        return await service.run(pipeline, options=options)


def _echo_run_result(result: RunResult) -> None:
    """Output run result message based on status and display metrics.

    Args:
        result: RunResult object with execution outcome and metrics.
    """
    # Truncate run_id to first 8 chars for readability (like git short hash)
    short_run_id = result.run_id[:8] if len(result.run_id) > 8 else result.run_id

    if result.status == PipelineRunResult.SUCCESS:
        echo_info(f"Pipeline completed successfully (run_id: {short_run_id})")
        # Display statistics for SUCCESS
        echo_info(f"  - Bronze records:      {result.records_fetched}")
        echo_info(f"  - Silver records:      {result.records_silver}")
        if result.records_gold > 0:
            echo_info(f"  - Gold records:        {result.records_gold}")
        if result.records_quarantined > 0:
            echo_warning(f"  - Quarantined (DQ):    {result.records_quarantined}")
        else:
            echo_info("  - Quarantined (DQ):    0")

    elif result.status == PipelineRunResult.DRY_RUN:
        echo_info(f"Dry-run completed (no changes made) (run_id: {short_run_id})")

    elif result.status == PipelineRunResult.SHUTDOWN:
        echo_warning(f"Pipeline was gracefully shut down (run_id: {short_run_id})")
        # Display partial statistics
        echo_info(f"  - Processed so far:    {result.records_fetched}")

    elif result.status == PipelineRunResult.FAILED:
        echo_error(
            f"Pipeline failed (run_id: {short_run_id})",
            result.error_message or "Unknown error",
        )
        # Display statistics before failure
        echo_info(f"  - Processed before failure: {result.records_fetched}")


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
@click.option(
    "--start-offset",
    type=int,
    default=None,
    help="Start extraction from specific record offset (skips checkpoint). "
    "Use after crash to resume from known position.",
)
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
@click.option(
    "--health-server/--no-health-server",
    "health_server",
    default=True,
    help="Enable/disable HTTP health server during execution.",
    show_default=True,
)
@click.option(
    "--health-port",
    type=int,
    default=DEFAULT_HEALTH_SERVER_PORT,
    help="Port for the HTTP health server.",
    show_default=True,
)
@click.option(
    "--use-cached-bronze/--no-cached-bronze",
    "use_cached_bronze",
    default=False,
    help="Load data from Bronze cache instead of API",
    show_default=True,
)
@click.option(
    "--cached-bronze-date",
    type=str,
    default=None,
    help="Filter Bronze cache by date (YYYY-MM-DD)",
)
@click.option(
    "--cached-bronze-path",
    type=click.Path(exists=True),
    default=None,
    help="Explicit path to Bronze cache directory",
)
def run(
    pipeline: str,
    run_type: str,
    resume: bool,
    start_offset: int | None,
    limit: int | None,
    input_csv: str | None,
    filter_column: str | None,
    filter_field: str | None,
    dry_run: bool,
    yes: bool,
    vacuum_after_run: bool | None,
    vacuum_retention_days: int | None,
    debug: bool,
    health_server: bool,
    health_port: int,
    use_cached_bronze: bool,
    cached_bronze_date: str | None,
    cached_bronze_path: str | None,
) -> None:
    """Run an ETL pipeline.

    Args:
        pipeline: Pipeline.
        run_type: Type of pipeline run.
        resume: Whether to resume.
        start_offset: Start offset.
        limit: Maximum number of records to process.
        input_csv: Input csv.
        filter_column: Filter column.
        filter_field: Field name to apply filter on.
        dry_run: Dry run mode flag.
        yes: Whether to yes.
        vacuum_after_run: Whether to vacuum after run.
        vacuum_retention_days: Vacuum retention days.
        debug: Whether to debug.
        health_server: Whether to health server.
        health_port: Health port.
        use_cached_bronze: Whether to use cached bronze.
        cached_bronze_date: Cached bronze date.
        cached_bronze_path: File path for cached bronze.
    """
    validate_options(start_offset, run_type, resume)

    # Handle confirmation for destructive operations (CLI responsibility)
    try:
        should_continue = handle_destructive_run_confirmation(
            pipeline, run_type, dry_run, yes
        )
    except click.Abort:
        raise
    except BioETLError as exc:
        handle_cli_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_CLEANUP_PREVIEW_ERROR",
        )
        return
    except Exception as exc:
        # reason_code=CLI_CLEANUP_PREVIEW_UNEXPECTED_ERROR
        handle_cli_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_CLEANUP_PREVIEW_UNEXPECTED_ERROR",
        )
        return
    if not should_continue:
        return

    options = build_run_options(
        run_type=run_type,
        resume=resume,
        start_offset=start_offset,
        limit=limit,
        input_csv=input_csv,
        filter_column=filter_column,
        filter_field=filter_field,
        dry_run=dry_run,
        vacuum_after_run=vacuum_after_run,
        vacuum_retention_days=vacuum_retention_days,
        debug=debug,
        use_cached_bronze=use_cached_bronze,
        cached_bronze_date=cached_bronze_date,
        cached_bronze_path=cached_bronze_path,
    )

    # Display health server info
    echo_health_server_info(health_server, health_port)

    # Run pipeline via service
    try:
        result = execute_run(
            pipeline=pipeline,
            options=options,
            health_server=health_server,
            health_port=health_port,
        )
    except PipelineNotFoundError as exc:
        handle_cli_failure(exc, pipeline=pipeline, reason_code="CLI_RUN_CONFIG_ERROR")
    except BioETLError as exc:
        handle_cli_failure(exc, pipeline=pipeline, reason_code="CLI_RUN_DOMAIN_ERROR")
    except KeyboardInterrupt as exc:
        handle_cli_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_RUN_SIGINT",
        )
    except Exception as exc:
        # reason_code=CLI_RUN_UNEXPECTED_ERROR
        handle_cli_failure(
            exc,
            pipeline=pipeline,
            reason_code="CLI_RUN_UNEXPECTED_ERROR",
        )

    # Map status to exit code and output result
    exit_code = _map_status_to_exit_code(result.status, result.error_type)
    _echo_run_result(result)
    sys.exit(exit_code)


# Re-export helpers for backward compatibility with tests
# These are imported by tests/unit/interfaces/test_cli.py
_get_runner_logger = get_runner_logger
_handle_destructive_run_confirmation = handle_destructive_run_confirmation
_preview_cleanup = show_cleanup_preview
_validate_start_offset = validate_options
