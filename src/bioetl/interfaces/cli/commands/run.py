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
    RunExecutionRequest,
)
from bioetl.composition.entrypoints import (
    get_pipeline_runner_service,
    push_metrics_to_gateway,
)
from bioetl.composition.registry import PipelineRegistry
from bioetl.interfaces.cli.commands.health_server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
    health_server_context,
)
from bioetl.interfaces.cli.commands.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.run_command_policy import (
    execute_run_step,
)
from bioetl.interfaces.cli.commands.run_command_policy import (
    finalize_run_step,
)
from bioetl.interfaces.cli.commands.run_command_policy import (
    handle_destructive_step,
    handle_cli_failure,
    map_status_to_exit_code,
    prepare_run_request,
)
from bioetl.interfaces.cli.commands.run_helpers import (
    get_runner_logger,
    handle_destructive_run_confirmation,
    resolve_context_registry,
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
    """Validate --start-offset constraints; sys.exit on error."""
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
    """Build RunOptions from CLI parameters."""
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
    request: RunExecutionRequest,
    registry: PipelineRegistry | None = None,
) -> RunResult:
    """Execute run and always flush metrics at command boundary.

    Args:
        request: Prepared run request with pipeline, options, and health config.

    Returns:
        RunResult with pipeline execution status and record counts.
    """

    async def _run_pipeline_with_registry(
        request: RunExecutionRequest,
    ) -> RunResult:
        return await _run_pipeline_async(
            request.pipeline,
            request.options,
            health_server_enabled=request.health_server,
            health_port=request.health_port,
            registry=registry,
        )

    return _CLI_RUN_ORCHESTRATION_SERVICE.execute_pipeline(
        request=request,
        run_pipeline_async=_run_pipeline_with_registry,
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
    registry: PipelineRegistry | None = None,
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
        service = get_pipeline_runner_service(registry=registry)
        return await service.run(pipeline, options=options)

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
@click.pass_context
def run(
    ctx: click.Context,
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
    registry = resolve_context_registry(ctx)
    if not handle_destructive_step(
        pipeline=pipeline,
        run_type=run_type,
        dry_run=dry_run,
        yes=yes,
    ):
        return
    request = prepare_run_request(
        service=_CLI_RUN_ORCHESTRATION_SERVICE,
        pipeline=pipeline,
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
        health_server=health_server,
        health_port=health_port,
        use_cached_bronze=use_cached_bronze,
        cached_bronze_date=cached_bronze_date,
        cached_bronze_path=cached_bronze_path,
        exit_func=_exit_with_code,
    )
    echo_health_server_info(request.health_server, request.health_port)
    result = execute_run_step(
        request=request,
        execute_run=lambda prepared_request: execute_run(
            request=prepared_request,
            registry=registry,
        ),
    )
    finalize_run_step(
        result=result,
        result_presenter=_echo_run_result,
        exit_func=_exit_with_code,
    )


# Re-export helpers for backward compatibility with tests
_get_runner_logger = get_runner_logger
_handle_destructive_run_confirmation = handle_destructive_run_confirmation
_preview_cleanup = show_cleanup_preview
_validate_start_offset = validate_options
