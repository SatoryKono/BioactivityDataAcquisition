"""Run command for BioETL CLI.

Implements the main pipeline execution command.
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import click

from bioetl.application.core.shutdown import PipelineShutdownError
from bioetl.composition.entrypoints import (
    RunOptions,
    create_pipeline_runner,
    preview_cleanup,
)
from bioetl.composition.registry import get_default_registry
from bioetl.interfaces.cli.formatters import (
    echo_cleanup_preview,
    echo_dry_run_prefix,
    echo_error,
    echo_info,
    echo_warning,
)
from bioetl.interfaces.orchestration.signals import setup_shutdown_handlers

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.ports import LoggerPort


def validate_pipeline_name(
    _ctx: click.Context | None, _param: click.Parameter | None, value: str
) -> str:
    """Validate pipeline name against the registry at runtime.

    Args:
        _ctx: Click context (unused).
        _param: Click parameter (unused).
        value: Pipeline name to validate.

    Returns:
        Validated pipeline name.

    Raises:
        click.BadParameter: If pipeline name is not in registry.
    """
    registry = get_default_registry()
    available = registry.list_pipelines()
    if value not in available:
        raise click.BadParameter(f"Unknown pipeline: {value}. Available: {available}")
    return value


def _get_runner_logger(runner: PipelineRunner) -> LoggerPort | None:
    """Get logger from runner with fallback.

    Args:
        runner: PipelineRunner instance.

    Returns:
        Logger instance (LoggerPort) or None if not found.
    """
    logger = getattr(runner, "logger", None)
    if logger is None:
        logger = getattr(runner, "_logger", None)
    return logger


async def _preview_cleanup_async(pipeline: str) -> None:
    """Preview what data would be cleared in dry-run mode.

    Args:
        pipeline: Pipeline name.
    """
    preview_result = await preview_cleanup(pipeline)
    echo_cleanup_preview(preview_result)


def _preview_cleanup(pipeline: str) -> None:
    """Sync wrapper for preview_cleanup_async.

    Args:
        pipeline: Pipeline name.
    """
    try:
        asyncio.run(_preview_cleanup_async(pipeline))
    except Exception as e:
        echo_error("Error previewing cleanup", str(e))


def _handle_destructive_run_confirmation(
    pipeline: str, run_type: str, dry_run: bool, yes: bool
) -> bool:
    """Handle confirmation for rebuild/backfill runs.

    Args:
        pipeline: Pipeline name.
        run_type: Type of run.
        dry_run: Whether this is a dry run.
        yes: Whether to skip confirmation.

    Returns:
        True if should continue with pipeline execution, False if should exit early.
    """
    if run_type not in ("rebuild", "backfill"):
        return True

    if dry_run:
        echo_dry_run_prefix(f"Would clear data for pipeline: {pipeline}")
        echo_dry_run_prefix(f"Run type: {run_type}")
        _preview_cleanup(pipeline)
        return False

    if not yes:
        echo_warning(f"{run_type} will clear existing data for {pipeline}.")
        if not click.confirm("Do you want to continue?"):
            echo_info("Operation cancelled.")
            sys.exit(0)

    return True


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
) -> None:
    """Run an ETL pipeline."""
    if not _handle_destructive_run_confirmation(pipeline, run_type, dry_run, yes):
        return

    try:
        options = RunOptions(
            run_type=run_type,
            resume=resume,
            limit=limit,
            input_csv=input_csv,
            filter_column=filter_column,
            filter_field=filter_field,
            dry_run=dry_run,
            vacuum_after_run=vacuum_after_run if vacuum_after_run else None,
            vacuum_retention_days=vacuum_retention_days,
        )
        runner = create_pipeline_runner(pipeline, options)
    except (ValueError, FileNotFoundError) as e:
        echo_error("Configuration error", str(e))
        sys.exit(1)
    except Exception as e:
        echo_error("Initialization failed", str(e))
        sys.exit(1)

    logger = _get_runner_logger(runner)
    if logger is None:
        echo_error("Critical: Logger not initialized.")
        sys.exit(1)

    shutdown_signal = getattr(runner, "shutdown_signal", None)
    if shutdown_signal is not None:
        setup_shutdown_handlers(shutdown_signal, logger)

    logger.info("Starting pipeline run")
    try:
        asyncio.run(runner.run())
        logger.info("Pipeline completed successfully")
    except PipelineShutdownError:
        logger.warning("Pipeline run was gracefully shut down.")
        sys.exit(130)
    except Exception:
        logger.exception("Pipeline failed with an unhandled exception.")
        sys.exit(1)
