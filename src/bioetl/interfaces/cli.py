"""Command-line interface for BioETL.

This is the primary entry point for running pipelines from the command line.
It acts as the "Composition Root" for the application, where dependencies
are assembled and the pipeline is executed.
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING
from uuid import uuid4

import click

from bioetl.application.core.shutdown import PipelineShutdownError
from bioetl.composition.bootstrap import (
    bootstrap_checkpoint,
    bootstrap_cleanup,
    bootstrap_pipeline,
    bootstrap_quarantine,
    load_pipeline_config,
)
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.registry import PipelineRegistry
from bioetl.domain.context import PipelineRunContext
from bioetl.domain.types import RunType
from bioetl.interfaces.orchestration.signals import setup_shutdown_handlers

if TYPE_CHECKING:
    import structlog

    from bioetl.application.core.runner import PipelineRunner


async def _preview_cleanup_async(pipeline: str) -> None:
    """Preview what data would be cleared in dry-run mode.

    Delegates to CleanupService.preview() for clean architecture.

    Args:
        pipeline: Pipeline name
    """
    config = load_pipeline_config(pipeline)
    cleanup_service = bootstrap_cleanup()

    preview = await cleanup_service.preview(
        silver_table=config.silver_table,
        gold_table=config.gold_table,
    )

    click.echo("\nFiles/directories that would be cleared:")

    # Display Silver info
    if preview.silver.exists:
        click.echo(
            f"  Silver: {preview.silver.path} ({preview.silver.file_count} files)"
        )
    else:
        click.echo(f"  Silver: {preview.silver.path} (does not exist)")

    # Display Gold info
    if preview.gold:
        if preview.gold.exists:
            click.echo(f"  Gold: {preview.gold.path} ({preview.gold.file_count} files)")
        else:
            click.echo(f"  Gold: {preview.gold.path} (does not exist)")

    click.echo(f"\nTotal items that would be cleared: ~{preview.total_files}")
    click.echo("\nNo changes were made (dry-run mode).")


def _preview_cleanup(pipeline: str) -> None:
    """Preview what data would be cleared in dry-run mode.

    Sync wrapper for CLI that calls async CleanupService.preview().

    Args:
        pipeline: Pipeline name
    """
    try:
        asyncio.run(_preview_cleanup_async(pipeline))
    except Exception as e:
        click.echo(f"Error previewing cleanup: {e}", err=True)


def validate_pipeline_name(
    _ctx: click.Context | None, _param: click.Parameter | None, value: str
) -> str:
    """Validate pipeline name against the registry at runtime."""
    available = PipelineRegistry.list_pipelines()
    if value not in available:
        raise click.BadParameter(f"Unknown pipeline: {value}. Available: {available}")
    return value


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
        click.echo(f"[DRY-RUN] Would clear data for pipeline: {pipeline}")
        click.echo(f"[DRY-RUN] Run type: {run_type}")
        _preview_cleanup(pipeline)
        return False

    if not yes:
        click.echo(f"WARNING: {run_type} will clear existing data for {pipeline}.")
        if not click.confirm("Do you want to continue?"):
            click.echo("Operation cancelled.")
            sys.exit(0)

    return True


def _get_runner_logger(runner: PipelineRunner) -> structlog.BoundLogger | None:
    """Get logger from runner with fallback.

    Args:
        runner: PipelineRunner instance.

    Returns:
        Logger instance or None if not found.
    """
    logger = getattr(runner, "logger", None)
    if logger is None:
        logger = getattr(runner, "_logger", None)
    return logger


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """BioETL - Bioactivity Data ETL Pipeline."""
    pass


@cli.command()
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
) -> None:
    """Run an ETL pipeline."""
    # Handle rebuild/backfill confirmation before any heavy initialization
    if not _handle_destructive_run_confirmation(pipeline, run_type, dry_run, yes):
        return

    run_id = uuid4()

    try:
        ctx = PipelineRunContext(
            pipeline_name=pipeline,
            run_id=run_id,
            run_type=RunType(run_type),
            resume=resume,
            limit=limit,
            input_csv=input_csv,
            filter_column=filter_column,
            filter_field=filter_field,
            dry_run=dry_run,
        )
        runner = bootstrap_pipeline(ctx)
    except (ValueError, FileNotFoundError) as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Initialization failed: {e}", err=True)
        sys.exit(1)

    logger = _get_runner_logger(runner)
    if logger is None:
        click.echo("Critical: Logger not initialized.", err=True)
        sys.exit(1)

    setup_shutdown_handlers(getattr(runner, "shutdown_signal", None))

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


@cli.group()
def quarantine() -> None:
    """Manage quarantine (failed records)."""
    pass


@quarantine.command("inspect")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option("--limit", type=int, default=100, help="Maximum records to show")
def quarantine_inspect(pipeline: str, limit: int) -> None:
    """Inspect quarantined records."""
    click.echo(f"Inspecting quarantine for {pipeline} (limit {limit})...")

    # Initialize infrastructure directly via bootstrap (read-only op)
    quarantine_service = bootstrap_quarantine()

    # Run async inspection
    async def _inspect() -> None:
        records = await quarantine_service.inspect(pipeline=pipeline, limit=limit)
        if not records:
            click.echo("No records found.")
            return

        for rec in records:
            click.echo(
                f"Error: {rec.get('error_code')} | Payload: {rec.get('payload')}"
            )

    asyncio.run(_inspect())


@cli.group()
def checkpoint() -> None:
    """Manage checkpoints."""
    pass


@checkpoint.command("list")
@click.option("--pipeline", required=True, help="Pipeline name")
def checkpoint_list(pipeline: str) -> None:
    """List all checkpoints."""
    click.echo(f"Listing checkpoints for {pipeline}...")

    checkpoint_service = bootstrap_checkpoint(pipeline)

    async def _list() -> None:
        checkpoints = await checkpoint_service.list_all()
        for cp in checkpoints:
            click.echo(f"- {cp}")

    asyncio.run(_list())


def main() -> None:
    """Main entry point."""
    # Explicit registration of all pipeline factories
    register_all_pipelines()
    cli()


if __name__ == "__main__":
    main()
