"""Run command for BioETL CLI.

Implements the main pipeline execution command using PipelineRunnerService.
"""

from __future__ import annotations

import asyncio
import sys
from typing import NoReturn

import click

from bioetl.application.services import (
    PipelineRunResult,
    RunOptions,
    RunResult,
)
from bioetl.application.services.cli_run_orchestration_service import (
    CliRunOrchestrationService,
)
from bioetl.composition.entrypoints import (
    get_pipeline_runner_service,
    push_metrics_to_gateway,
)
from bioetl.interfaces.cli.commands.health_server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
    health_server_context,
)
from bioetl.interfaces.cli.commands.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.run_command_policy import (
    execute_run_step as _execute_run_step_policy,
)
from bioetl.interfaces.cli.commands.run_command_policy import (
    finalize_run_step as _finalize_run_step_policy,
)
from bioetl.interfaces.cli.commands.run_command_policy import (
    handle_cli_failure,
    map_status_to_exit_code,
)
from bioetl.interfaces.cli.commands.run_command_policy import (
    handle_destructive_step as _handle_destructive_step_policy,
)
from bioetl.interfaces.cli.commands.run_helpers import (
    get_runner_logger,
    handle_destructive_run_confirmation,
    show_cleanup_preview,
    validate_pipeline_name,
)
from bioetl.interfaces.cli.commands.run_result_presenter import (
    echo_run_result as _echo_run_result,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error

__all__ = [
    "build_run_options",
    "execute_run",
    "handle_cli_failure",
    "run",
    "validate_options",
]

_CLI_RUN_ORCHESTRATION_SERVICE = CliRunOrchestrationService()


def _exit_with_code(code: int | str | None = None) -> NoReturn:
    """Typed wrapper around sys.exit for policy flow injection."""
    sys.exit(code)


def validate_options(start_offset: int | None, run_type: str, resume: bool) -> None:
    """Validate --start-offset constraints; sys.exit on error.

    Args:
        start_offset: Record offset to start extraction from; None when not provided.
        run_type: Type of run (e.g., 'incremental', 'rebuild', 'backfill'); start_offset
            is only valid for incremental runs.
        resume: When True, indicates checkpoint-based resume; incompatible with
            start_offset.
    """
    validation = _CLI_RUN_ORCHESTRATION_SERVICE.validate_start_offset(
        start_offset=start_offset,
        run_type=run_type,
        resume=resume,
    )
    if validation.is_valid:
        return
    if validation.error_message is not None:
        echo_error(validation.error_message)
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
    """Build RunOptions from CLI parameters.

    Args:
        run_type: Type of run ('incremental', 'backfill', or 'rebuild').
        resume: When True, resumes from the last saved checkpoint.
        start_offset: Record offset to start extraction from; ignored when None.
        limit: Maximum number of records to process; no limit when None.
        input_csv: Path to CSV file containing filter IDs; disables CSV filtering when None.
        filter_column: Column name in the CSV that holds filter IDs; uses 'id' when None.
        filter_field: API field name to filter by; uses provider default when None.
        dry_run: When True, previews cleanup without executing the pipeline.
        vacuum_after_run: When True, runs VACUUM after a successful run; uses YAML config
            when None.
        vacuum_retention_days: Minimum file age for VACUUM removal in days; uses YAML
            config when None.
        debug: When True, sets log level to DEBUG for verbose output.
        use_cached_bronze: When True, loads data from Bronze cache instead of the live API.
        cached_bronze_date: Date filter for Bronze cache in 'YYYY-MM-DD' format; ignored
            when None.
        cached_bronze_path: Explicit path to Bronze cache directory; uses default when None.

    Returns:
        RunOptions instance configured with the provided CLI parameter values.
    """
    return _CLI_RUN_ORCHESTRATION_SERVICE.build_options(
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


def execute_run(
    pipeline: str,
    options: RunOptions,
    health_server: bool,
    health_port: int,
) -> RunResult:
    """Execute run and always flush metrics at command boundary.

    Args:
        pipeline: Pipeline name to execute.
        options: RunOptions with run type, limits, and filter settings.
        health_server: When True, enables the HTTP health server during execution.
        health_port: TCP port the health server listens on.

    Returns:
        RunResult with pipeline execution status and record counts.
    """
    return _CLI_RUN_ORCHESTRATION_SERVICE.execute_pipeline(
        pipeline=pipeline,
        options=options,
        health_server=health_server,
        health_port=health_port,
        run_pipeline_async=_run_pipeline_async,
        run_coroutine=asyncio.run,
        flush_metrics=push_metrics_to_gateway,
    )


def _map_status_to_exit_code(
    status: PipelineRunResult,
    error_type: str | None,
) -> ExitCode:
    """Map run status to CLI exit code."""
    return map_status_to_exit_code(status, error_type)


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
    ensure_metrics_server_started()
    async with health_server_context(
        enabled=health_server_enabled,
        port=health_port,
    ):
        service = get_pipeline_runner_service()
        return await service.run(pipeline, options=options)


def _handle_destructive_step(
    *,
    pipeline: str,
    run_type: str,
    dry_run: bool,
    yes: bool,
) -> bool:
    """Run destructive confirmation/preview step with CLI error policy."""
    return _handle_destructive_step_policy(
        pipeline=pipeline,
        run_type=run_type,
        dry_run=dry_run,
        yes=yes,
    )


def _execute_run_step(
    *,
    pipeline: str,
    options: RunOptions,
    health_server: bool,
    health_port: int,
) -> RunResult:
    """Run pipeline execution step with CLI failure mapping."""
    return _execute_run_step_policy(
        pipeline=pipeline,
        options=options,
        health_server=health_server,
        health_port=health_port,
        execute_run=execute_run,
    )


def _finalize_run_step(result: RunResult) -> None:
    """Echo result and terminate command with mapped exit code."""
    _finalize_run_step_policy(
        result=result,
        result_presenter=_echo_run_result,
        exit_func=_exit_with_code,
    )


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
    """Run an ETL pipeline."""
    validate_options(start_offset, run_type, resume)
    if not _handle_destructive_step(
        pipeline=pipeline,
        run_type=run_type,
        dry_run=dry_run,
        yes=yes,
    ):
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
    echo_health_server_info(health_server, health_port)
    result = _execute_run_step(
        pipeline=pipeline,
        options=options,
        health_server=health_server,
        health_port=health_port,
    )
    _finalize_run_step(result)


# Re-export helpers for backward compatibility with tests
_get_runner_logger = get_runner_logger
_handle_destructive_run_confirmation = handle_destructive_run_confirmation
_preview_cleanup = show_cleanup_preview
_validate_start_offset = validate_options
