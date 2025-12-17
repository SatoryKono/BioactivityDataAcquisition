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
from bioetl.domain.types import RunType
from bioetl.interfaces.bootstrap import bootstrap_pipeline
from bioetl.interfaces.orchestration.runner import PipelineRunner
from bioetl.interfaces.orchestration.signals import setup_shutdown_handlers

if TYPE_CHECKING:
    pass


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """BioETL - Bioactivity Data ETL Pipeline."""
    pass


@cli.command()
@click.option(
    "--pipeline",
    type=click.Choice(["chembl_activity"]),
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
def run(pipeline: str, run_type: str, resume: bool, limit: int | None) -> None:
    """Run an ETL pipeline."""
    run_id = uuid4()

    # Bootstrap the entire pipeline with all its dependencies
    pipeline_obj = bootstrap_pipeline(
        pipeline_name=pipeline,
        run_id=run_id,
        run_type=RunType(run_type),
        resume=resume,
        limit=limit,
    )
    logger = pipeline_obj.logger

    # The runner is the infrastructure component that executes the pipeline
    runner = PipelineRunner(
        config=pipeline_obj.config,
        runtime=pipeline_obj.runtime,
        services=pipeline_obj.services,
        context=pipeline_obj.context,
        executor=pipeline_obj.executor,
        checkpoint_manager=pipeline_obj.checkpoint_manager,
        shutdown_signal=pipeline_obj.shutdown_signal,
        logger=logger,
    )

    # Set up OS signal handlers to gracefully trigger the shutdown signal
    setup_shutdown_handlers(pipeline_obj.shutdown_signal)

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


# ... (other CLI commands like quarantine, checkpoint remain the same for now)
# Note: They would also need to be updated to use the new bootstrap/service model
# if they have complex logic, but for now they are simple and can be addressed later.


@cli.group()
def quarantine() -> None:
    """Manage quarantine (failed records)."""
    pass


@quarantine.command("inspect")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option("--limit", type=int, default=100, help="Maximum records to show")
def quarantine_inspect(pipeline: str, limit: int) -> None:
    """Inspect quarantined records."""
    # This part would also be refactored to use a dedicated service
    click.echo(f"Inspecting quarantine for {pipeline} (limit {limit})...")


@cli.group()
def checkpoint() -> None:
    """Manage checkpoints."""
    pass


@checkpoint.command("list")
def checkpoint_list() -> None:
    """List all checkpoints."""
    click.echo("Listing checkpoints...")


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
