"""Vacuum commands for BioETL CLI.

Implements vacuum operations for Delta tables storage reclamation.
"""

from __future__ import annotations

import asyncio

import click

from bioetl.composition.entrypoints import get_lifecycle_service, get_vacuum_service
from bioetl.interfaces.cli.formatters import (
    echo_dry_run_prefix,
    echo_info,
    echo_vacuum_all_summary,
    echo_vacuum_result,
)


@click.command("vacuum")
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
            echo_dry_run_prefix(f"Would vacuum {table} (retention: {retention_days}d)")

        files_removed = await lifecycle.vacuum(
            table=table,
            retention_days=retention_days,
            dry_run=dry_run,
        )

        if dry_run:
            echo_info(f"Would remove {files_removed} files")
        else:
            echo_info(f"Removed {files_removed} files")

    asyncio.run(_run())


@click.command("vacuum-all")
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
    service = get_vacuum_service()
    tables_to_vacuum = service.collect_tables(layer)

    if not tables_to_vacuum:
        echo_info("No tables found to vacuum.")
        return

    async def _run() -> None:
        result = await service.vacuum_all(
            tables=tables_to_vacuum,
            retention_days=retention_days,
            dry_run=dry_run,
        )

        for table_result in result.results:
            echo_vacuum_result(table_result, dry_run)

        echo_vacuum_all_summary(result)

    asyncio.run(_run())
