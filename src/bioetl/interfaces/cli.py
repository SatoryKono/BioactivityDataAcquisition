"""Command-line interface for BioETL.

This is the primary entry point for running pipelines from the command line.
It acts as the "Composition Root" for the application, where dependencies
are assembled and the pipeline is executed.
"""

from __future__ import annotations

import asyncio
import sys
from uuid import uuid4

import click

from bioetl.application.core.shutdown import PipelineShutdownError
from bioetl.composition.bootstrap import (
    bootstrap_checkpoint,
    bootstrap_pipeline,
    bootstrap_quarantine,
)
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.registry import PipelineRegistry
from bioetl.domain.context import PipelineRunContext
from bioetl.domain.types import RunType
from bioetl.infrastructure.config import get_settings
from bioetl.interfaces.observability import start_metrics_server
from bioetl.interfaces.orchestration.signals import setup_shutdown_handlers


def validate_pipeline_name(_ctx, _param, value):
    """Validate pipeline name against the registry at runtime."""
    available = PipelineRegistry.list_pipelines()
    if value not in available:
        raise click.BadParameter(f"Unknown pipeline: {value}. Available: {available}")
    return value


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
def run(
    pipeline: str,
    run_type: str,
    resume: bool,
    limit: int | None,
    input_csv: str | None,
    filter_column: str | None,
    filter_field: str | None,
) -> None:
    """Run an ETL pipeline."""
    run_id = uuid4()

    try:
        # Bootstrap returns a fully constructed runner
        ctx = PipelineRunContext(
            pipeline_name=pipeline,
            run_id=run_id,
            run_type=RunType(run_type),
            resume=resume,
            limit=limit,
            input_csv=input_csv,
            filter_column=filter_column,
            filter_field=filter_field,
        )
        runner = bootstrap_pipeline(ctx)
    except (ValueError, FileNotFoundError) as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Initialization failed: {e}", err=True)
        sys.exit(1)

    # Use explicit logger if available, otherwise fallback is necessary but unlikely if bootstrap succeeded
    logger = getattr(runner, "logger", None)
    if logger is None:
        # Fallback for old runner versions or if runner structure changed
        logger = getattr(runner, "_logger", None)

    if logger is None:
        click.echo("Critical: Logger not initialized.", err=True)
        sys.exit(1)

    # Set up OS signal handlers to gracefully trigger the shutdown signal
    setup_shutdown_handlers(getattr(runner, "shutdown_signal", None))

    # Start Prometheus metrics server
    try:
        settings = get_settings()
        start_metrics_server(settings.metrics_port)
    except Exception as e:
        logger.warning("Failed to start metrics server", error=str(e))

    logger.info("Starting pipeline run")
    try:
        asyncio.run(runner.run())
        logger.info("Pipeline completed successfully")
    except PipelineShutdownError:
        logger.warning("Pipeline run was gracefully shut down.")
        sys.exit(130)  # Exit code for command-line interrupt
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
