"""Command-line interface for BioETL.

This is the primary entry point for running pipelines from the command line.
It delegates to composition/entrypoints.py for all pipeline operations.
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import click

from bioetl import __version__
from bioetl.application.core.shutdown import PipelineShutdownError
from bioetl.composition.entrypoints import (
    RunOptions,
    create_pipeline_runner,
    get_checkpoint_manager,
    get_lifecycle_service,
    get_quarantine_manager,
    preview_cleanup,
)
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.registry import get_default_registry
from bioetl.interfaces.orchestration.signals import setup_shutdown_handlers

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.ports import LoggerPort


async def _preview_cleanup_async(pipeline: str) -> None:
    """Preview what data would be cleared in dry-run mode."""
    preview_result = await preview_cleanup(pipeline)

    click.echo("\nFiles/directories that would be cleared:")

    # Display Silver info
    if preview_result.silver.exists:
        click.echo(
            f"  Silver: {preview_result.silver.path} "
            f"({preview_result.silver.file_count} files)"
        )
    else:
        click.echo(f"  Silver: {preview_result.silver.path} (does not exist)")

    # Display Gold info
    if preview_result.gold:
        if preview_result.gold.exists:
            click.echo(
                f"  Gold: {preview_result.gold.path} "
                f"({preview_result.gold.file_count} files)"
            )
        else:
            click.echo(f"  Gold: {preview_result.gold.path} (does not exist)")

    click.echo(f"\nTotal items that would be cleared: ~{preview_result.total_files}")
    click.echo("\nNo changes were made (dry-run mode).")


def _preview_cleanup(pipeline: str) -> None:
    """Sync wrapper for preview_cleanup_async."""
    try:
        asyncio.run(_preview_cleanup_async(pipeline))
    except Exception as e:
        click.echo(f"Error previewing cleanup: {e}", err=True)


def validate_pipeline_name(
    _ctx: click.Context | None, _param: click.Parameter | None, value: str
) -> str:
    """Validate pipeline name against the registry at runtime."""
    registry = get_default_registry()
    available = registry.list_pipelines()
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


@click.group()
@click.version_option(version=__version__)
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
    # Handle rebuild/backfill confirmation before any heavy initialization
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
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Initialization failed: {e}", err=True)
        sys.exit(1)

    logger = _get_runner_logger(runner)
    if logger is None:
        click.echo("Critical: Logger not initialized.", err=True)
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

    # Use application-layer QuarantineManager via entrypoints
    quarantine_manager = get_quarantine_manager(pipeline)

    # Run async inspection
    async def _inspect() -> None:
        records = await quarantine_manager.inspect(limit=limit)
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

    # Use application-layer CheckpointManager via entrypoints
    checkpoint_manager = get_checkpoint_manager(pipeline)

    async def _list() -> None:
        checkpoints = await checkpoint_manager.list_all()
        for cp in checkpoints:
            click.echo(f"- {cp}")

    asyncio.run(_list())


@cli.group()
def maintenance() -> None:
    """Maintenance operations for Delta tables."""
    pass


@maintenance.command("vacuum")
@click.argument("table")
@click.option(
    "--retention-days",
    "-r",
    default=7,
    help="Minimum age of files to remove (days)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without removing",
)
def vacuum_command(table: str, retention_days: int, dry_run: bool) -> None:
    """Vacuum Delta table to reclaim storage space.

    TABLE: Table name in format "provider.entity" (e.g., chembl.activity)

    Examples:

        bioetl maintenance vacuum chembl.activity

        bioetl maintenance vacuum chembl.activity --dry-run

        bioetl maintenance vacuum chembl.activity -r 30
    """
    lifecycle = get_lifecycle_service()

    async def _run() -> None:
        if dry_run:
            click.echo(f"[DRY-RUN] Would vacuum {table} (retention: {retention_days}d)")

        files_removed = await lifecycle.vacuum(
            table=table,
            retention_days=retention_days,
            dry_run=dry_run,
        )

        if dry_run:
            click.echo(f"Would remove {files_removed} files")
        else:
            click.echo(f"Removed {files_removed} files")

    asyncio.run(_run())


def _collect_vacuum_tables(layer: str) -> list[tuple[str, str]]:
    """Collect tables to vacuum from all pipeline configs."""
    from bioetl.composition.entrypoints import load_pipeline_config

    pipelines = get_default_registry().list_pipelines()

    silver_tables: set[str] = set()
    gold_tables: set[str] = set()

    for pipeline_name in pipelines:
        try:
            config = load_pipeline_config(pipeline_name)
            if config.silver_table:
                silver_tables.add(config.silver_table)
            if config.gold_table:
                gold_tables.add(config.gold_table)
        except FileNotFoundError:
            click.echo(f"Warning: Config not found for {pipeline_name}", err=True)

    tables: list[tuple[str, str]] = []
    if layer in ("all", "silver"):
        tables.extend((t, "silver") for t in sorted(silver_tables))
    if layer in ("all", "gold"):
        tables.extend((t, "gold") for t in sorted(gold_tables))

    return tables


async def _vacuum_table(
    lifecycle: MedallionLifecycleService,
    table_name: str,
    table_layer: str,
    retention_days: int,
    dry_run: bool,
) -> tuple[int, str | None]:
    """Vacuum a single table. Returns (files_removed, error_message or None)."""
    try:
        action = "Would vacuum" if dry_run else "Vacuuming"
        click.echo(
            f"{'[DRY-RUN] ' if dry_run else ''}{action} {table_layer}/{table_name}..."
        )

        files_removed = await lifecycle.vacuum(
            table=table_name,
            retention_days=retention_days,
            dry_run=dry_run,
        )

        result_verb = "Would remove" if dry_run else "Removed"
        click.echo(f"  {result_verb} {files_removed} files")
        return files_removed, None
    except Exception as e:
        click.echo(f"  Error: {e}", err=True)
        return 0, f"{table_layer}/{table_name}"


@maintenance.command("vacuum-all")
@click.option(
    "--retention-days",
    "-r",
    default=7,
    help="Minimum age of files to remove (days)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without removing",
)
@click.option(
    "--layer",
    type=click.Choice(["all", "silver", "gold"]),
    default="all",
    help="Which layer to vacuum (default: all)",
)
def vacuum_all_command(retention_days: int, dry_run: bool, layer: str) -> None:
    """Vacuum all Delta tables to reclaim storage space.

    Runs VACUUM on all registered Silver and Gold tables.

    Examples:

        bioetl maintenance vacuum-all

        bioetl maintenance vacuum-all --dry-run

        bioetl maintenance vacuum-all -r 30

        bioetl maintenance vacuum-all --layer silver
    """
    tables_to_vacuum = _collect_vacuum_tables(layer)

    if not tables_to_vacuum:
        click.echo("No tables found to vacuum.")
        return

    lifecycle = get_lifecycle_service()

    async def _run() -> None:
        total_files = 0
        failed_tables: list[str] = []

        for table_name, table_layer in tables_to_vacuum:
            files, error = await _vacuum_table(
                lifecycle, table_name, table_layer, retention_days, dry_run
            )
            total_files += files
            if error:
                failed_tables.append(error)

        result_verb = "would remove" if dry_run else "removed"
        click.echo(f"\nTotal: {result_verb} {total_files} files")
        if failed_tables:
            click.echo(f"Failed tables: {', '.join(failed_tables)}", err=True)

    asyncio.run(_run())


@maintenance.command("archive")
@click.argument("table")
@click.argument("target_path")
@click.option(
    "--remove-source",
    is_flag=True,
    help="Remove source table after archiving",
)
def archive_command(table: str, target_path: str, remove_source: bool) -> None:
    """Archive Delta table to cold storage.

    TABLE: Table name to archive

    TARGET_PATH: Destination path for archive
    """
    lifecycle = get_lifecycle_service()

    async def _run() -> None:
        files_archived = await lifecycle.archive(
            table=table,
            target_path=target_path,
            remove_source=remove_source,
        )

        click.echo(f"Archived {files_archived} files to {target_path}")

    asyncio.run(_run())


def main() -> None:
    """Main entry point."""
    # Explicit registration of all pipeline factories
    register_all_pipelines()
    cli()


if __name__ == "__main__":
    main()
