"""Command-line interface for BioETL.

Usage:
    bioetl run --pipeline chembl_activity --run-type incremental
    bioetl run --pipeline chembl_activity --run-type backfill --resume
    bioetl quarantine inspect --pipeline chembl_activity --limit 10
    bioetl checkpoint list
"""

import asyncio
import sys

import click

from bioetl.domain.types import RunType


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
    click.echo(f"🚀 Starting pipeline: {pipeline}")
    click.echo(f"   Run type: {run_type}")
    click.echo(f"   Resume: {resume}")

    # Convert run_type to enum
    run_type_enum = RunType(run_type)

    try:
        if pipeline == "chembl_activity":
            asyncio.run(_run_chembl_activity(run_type_enum, resume, limit))
        else:
            click.echo(f"❌ Unknown pipeline: {pipeline}", err=True)
            sys.exit(1)

        click.echo("✅ Pipeline completed successfully")

    except KeyboardInterrupt:
        click.echo("\n⚠️  Pipeline interrupted by user", err=True)
        sys.exit(130)

    except Exception as e:
        click.echo(f"❌ Pipeline failed: {e}", err=True)
        sys.exit(1)


async def _run_chembl_activity(
    run_type: RunType,
    resume: bool,
    limit: int | None,
) -> None:
    """Run ChEMBL Activity pipeline.

    Args:
        run_type: Type of run
        resume: Resume from checkpoint
        limit: Max records
    """
    from bioetl.application.pipelines.chembl_activity import (
        ChEMBLActivityPipelineFactory,
    )

    # Load configuration from environment
    import os

    factory = ChEMBLActivityPipelineFactory()
    pipeline = await factory.create(
        run_type=run_type,
        resume=resume,
        # From environment variables
        aws_endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        aws_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        s3_bucket_bronze=os.getenv("BIOETL_S3_BUCKET_BRONZE", "bioetl-bronze"),
        s3_bucket_silver=os.getenv("BIOETL_S3_BUCKET_SILVER", "bioetl-silver"),
        s3_bucket_checkpoints=os.getenv(
            "BIOETL_S3_BUCKET_CHECKPOINTS", "bioetl-checkpoints"
        ),
        redis_host=os.getenv("BIOETL_REDIS_HOST", "localhost"),
        redis_port=int(os.getenv("BIOETL_REDIS_PORT", "6379")),
    )

    await pipeline.run()


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
    asyncio.run(_quarantine_inspect(pipeline, limit, error_code))


async def _quarantine_inspect(
    pipeline: str,
    limit: int,
    error_code: str | None,
) -> None:
    """Inspect quarantine implementation."""
    import os

    from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine

    storage_options = {
        "AWS_ENDPOINT_URL": os.getenv("AWS_ENDPOINT_URL"),
        "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
    }

    quarantine = UnifiedQuarantine(
        base_path=f"s3://{os.getenv('BIOETL_S3_BUCKET_SILVER', 'bioetl-silver')}/common/quarantine",
        storage_options=(
            storage_options if storage_options["AWS_ENDPOINT_URL"] else None
        ),
    )

    records = quarantine.inspect(
        pipeline=pipeline,
        limit=limit,
        error_code=error_code,
    )

    if not records:
        click.echo(f"No quarantined records found for pipeline: {pipeline}")
        return

    click.echo(f"Found {len(records)} quarantined records:\n")

    for i, record in enumerate(records, 1):
        click.echo(f"[{i}] Error: {record['error_code']}")
        click.echo(f"    Time: {record['ingestion_ts']}")
        click.echo(f"    Status: {record['dq_status']}")
        click.echo(f"    Payload (truncated): {str(record['payload'])[:200]}...")
        click.echo()


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
    asyncio.run(_quarantine_stats(pipeline))


async def _quarantine_stats(pipeline: str) -> None:
    """Get quarantine statistics."""
    import os

    from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine

    storage_options = {
        "AWS_ENDPOINT_URL": os.getenv("AWS_ENDPOINT_URL"),
        "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
    }

    quarantine = UnifiedQuarantine(
        base_path=f"s3://{os.getenv('BIOETL_S3_BUCKET_SILVER', 'bioetl-silver')}/common/quarantine",
        storage_options=(
            storage_options if storage_options["AWS_ENDPOINT_URL"] else None
        ),
    )

    stats = quarantine.get_stats(pipeline)

    click.echo(f"Quarantine statistics for: {pipeline}\n")
    click.echo(f"Total records: {stats['total_records']}")
    click.echo(f"Oldest record: {stats['oldest_record']}")
    click.echo(f"Newest record: {stats['newest_record']}")
    click.echo(f"\nBy error code:")

    for error_code, count in stats["by_error_code"].items():
        click.echo(f"  {error_code}: {count}")

    click.echo(f"\nBy status:")
    for status, count in stats["by_status"].items():
        click.echo(f"  {status}: {count}")


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
    asyncio.run(_checkpoint_list())


async def _checkpoint_list() -> None:
    """List checkpoints implementation."""
    import os

    from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint

    checkpoint_storage = S3Checkpoint(
        bucket=os.getenv("BIOETL_S3_BUCKET_CHECKPOINTS", "bioetl-checkpoints"),
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        access_key=os.getenv("AWS_ACCESS_KEY_ID"),
        secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    pipelines = checkpoint_storage.list_all()

    if not pipelines:
        click.echo("No checkpoints found")
        return

    click.echo(f"Found {len(pipelines)} checkpoint(s):\n")

    for pipeline_name in pipelines:
        data = checkpoint_storage.load(pipeline_name)
        if data:
            watermark, run_id, metadata = data
            click.echo(f"Pipeline: {pipeline_name}")
            click.echo(f"  Watermark: {watermark}")
            click.echo(f"  Run ID: {run_id}")
            click.echo(f"  Metadata: {metadata}")
            click.echo()


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
    asyncio.run(_checkpoint_delete(pipeline))


async def _checkpoint_delete(pipeline: str) -> None:
    """Delete checkpoint implementation."""
    import os

    from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint

    checkpoint_storage = S3Checkpoint(
        bucket=os.getenv("BIOETL_S3_BUCKET_CHECKPOINTS", "bioetl-checkpoints"),
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        access_key=os.getenv("AWS_ACCESS_KEY_ID"),
        secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    checkpoint_storage.delete(pipeline)
    click.echo(f"✅ Checkpoint deleted for pipeline: {pipeline}")


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
