"""Command-line interface for BioETL.

Usage:
    bioetl run --pipeline chembl_activity --run-type incremental
    bioetl run --pipeline chembl_activity --run-type backfill --resume
    bioetl quarantine inspect --pipeline chembl_activity --limit 10
    bioetl checkpoint list
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING
from uuid import uuid4

import click

from bioetl.application.core.base import run_pipeline_flow
from bioetl.bootstrap import (
    ChEMBLActivityPipelineFactory,
    bootstrap,
    bootstrap_logger,
)
from bioetl.config import get_settings
from bioetl.domain.types import RunType

if TYPE_CHECKING:
    import structlog


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """BioETL - Bioactivity Data ETL Pipeline.

    Extract, transform, and load bioactivity data from multiple sources
    using Medallion Architecture (Bronze → Silver → Gold).
    """
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
    help="Type of run (default: incremental)",
)
@click.option(
    "--resume",
    is_flag=True,
    help="Resume from last checkpoint",
)
@click.option(
    "--limit",
    type=int,
    help="Maximum number of records to process",
)
def run(pipeline: str, run_type: str, resume: bool, limit: int | None) -> None:
    """Run an ETL pipeline.

    Examples:
        bioetl run --pipeline chembl_activity
        bioetl run --pipeline chembl_activity --run-type backfill --resume
        bioetl run --pipeline chembl_activity --limit 1000
    """
    run_id = uuid4()
    logger = bootstrap_logger(pipeline=pipeline, run_id=run_id)
    logger.info(
        "Starting pipeline",
        run_type=run_type,
        resume=resume,
        limit=limit,
    )

    # Convert run_type to enum
    run_type_enum = RunType(run_type)

    try:
        if pipeline == "chembl_activity":
            asyncio.run(_run_chembl_activity(run_type_enum, resume, limit, logger))
        else:
            logger.error("Unknown pipeline", pipeline=pipeline)
            sys.exit(1)

        logger.info("Pipeline completed successfully")

    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.exception("Pipeline failed", error=str(e))
        sys.exit(1)


async def _run_chembl_activity(
    run_type: RunType,
    resume: bool,
    limit: int | None,
    logger: structlog.BoundLogger,
) -> None:
    """Run ChEMBL Activity pipeline.

    Args:
        run_type: Type of run
        resume: Resume from checkpoint
        limit: Maximum number of records to process
        logger: Structured logger
    """
    # Initialize dependencies via Composition Root
    container = bootstrap()

    # Load configuration from centralized config
    settings = get_settings()

    pipeline = await ChEMBLActivityPipelineFactory.create(
        run_type=run_type,
        settings=settings,
        logger=logger,
        resume=resume,
        limit=limit,
        # Inject initialized services
        checkpoint=container.checkpoint,
        quarantine=container.quarantine,
        lock=container.lock,
        metrics=container.metrics,
    )

    await run_pipeline_flow(pipeline, logger)


@cli.group()
def quarantine() -> None:
    """Manage quarantine (failed records)."""
    pass


@quarantine.command("inspect")
@click.option(
    "--pipeline",
    required=True,
    help="Pipeline name",
)
@click.option(
    "--limit",
    type=int,
    default=100,
    help="Maximum records to show (default: 100)",
)
@click.option(
    "--error-code",
    help="Filter by error code",
)
def quarantine_inspect(pipeline: str, limit: int, error_code: str | None) -> None:
    """Inspect quarantined records.

    Examples:
        bioetl quarantine inspect --pipeline chembl_activity
        bioetl quarantine inspect --pipeline chembl_activity --error-code SCHEMA_VIOLATION
    """
    logger = bootstrap_logger(pipeline=pipeline, run_id=uuid4())
    asyncio.run(_quarantine_inspect(pipeline, limit, error_code, logger))


async def _quarantine_inspect(
    pipeline: str,
    limit: int,
    error_code: str | None,
    logger: structlog.BoundLogger,
) -> None:
    """Inspect quarantine implementation."""
    container = bootstrap()

    records = container.quarantine.inspect(
        pipeline=pipeline,
        limit=limit,
        error_code=error_code,
    )

    if not records:
        logger.info("No quarantined records found")
        return

    logger.info(f"Found {len(records)} quarantined records")

    for record in records:
        logger.info("Quarantined record", **record)


@quarantine.command("stats")
@click.option(
    "--pipeline",
    required=True,
    help="Pipeline name",
)
def quarantine_stats(pipeline: str) -> None:
    """Show quarantine statistics.

    Examples:
        bioetl quarantine stats --pipeline chembl_activity
    """
    logger = bootstrap_logger(pipeline=pipeline, run_id=uuid4())
    asyncio.run(_quarantine_stats(pipeline, logger))


async def _quarantine_stats(pipeline: str, logger: structlog.BoundLogger) -> None:
    """Get quarantine statistics."""
    container = bootstrap()
    stats = container.quarantine.get_stats(pipeline)

    logger.info("Quarantine statistics", **stats)


@cli.group()
def checkpoint() -> None:
    """Manage checkpoints."""
    pass


@checkpoint.command("list")
def checkpoint_list() -> None:
    """List all checkpoints.

    Examples:
        bioetl checkpoint list
    """
    logger = bootstrap_logger(pipeline="checkpoint", run_id=uuid4())
    asyncio.run(_checkpoint_list(logger))


async def _checkpoint_list(logger: structlog.BoundLogger) -> None:
    """List checkpoints implementation."""
    container = bootstrap()
    checkpoint_storage = container.checkpoint

    pipelines = checkpoint_storage.list_all()

    if not pipelines:
        logger.info("No checkpoints found")
        return

    logger.info(f"Found {len(pipelines)} checkpoint(s)")

    for pipeline_name in pipelines:
        data = checkpoint_storage.load(pipeline_name)
        if data:
            watermark, run_id, metadata = data
            logger.info(
                "Checkpoint details",
                pipeline_name=pipeline_name,
                watermark=watermark,
                run_id=run_id,
                metadata=metadata,
            )


@checkpoint.command("delete")
@click.option(
    "--pipeline",
    required=True,
    help="Pipeline name",
)
@click.confirmation_option(prompt="Are you sure you want to delete this checkpoint?")
def checkpoint_delete(pipeline: str) -> None:
    """Delete a checkpoint.

    Examples:
        bioetl checkpoint delete --pipeline chembl_activity
    """
    logger = bootstrap_logger(pipeline=pipeline, run_id=uuid4())
    asyncio.run(_checkpoint_delete(pipeline, logger))


async def _checkpoint_delete(pipeline: str, logger: structlog.BoundLogger) -> None:
    """Delete checkpoint implementation."""
    container = bootstrap()
    checkpoint_storage = container.checkpoint

    checkpoint_storage.delete(pipeline)
    logger.info("Checkpoint deleted")


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
