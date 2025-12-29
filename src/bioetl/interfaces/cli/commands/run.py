"""Run command for BioETL CLI.

Implements the main pipeline execution command.
"""

from __future__ import annotations

import asyncio
import sys

import click

from bioetl.application.core.shutdown import PipelineShutdownError
from bioetl.composition.entrypoints import RunOptions, create_pipeline_runner
from bioetl.interfaces.cli.commands.run_helpers import (
    get_runner_logger,
    handle_destructive_run_confirmation,
    show_cleanup_preview,
    validate_pipeline_name,
)
from bioetl.interfaces.cli.formatters import echo_error
from bioetl.interfaces.orchestration.signals import setup_shutdown_handlers

# Re-export helpers for backward compatibility with tests
# These are imported by tests/unit/interfaces/test_cli.py
_get_runner_logger = get_runner_logger
_handle_destructive_run_confirmation = handle_destructive_run_confirmation
_preview_cleanup = show_cleanup_preview


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
    if not handle_destructive_run_confirmation(pipeline, run_type, dry_run, yes):
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

    logger = get_runner_logger(runner)
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
