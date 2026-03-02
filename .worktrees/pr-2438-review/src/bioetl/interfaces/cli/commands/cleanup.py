"""Cleanup commands for BioETL CLI.

Implements Bronze layer cleanup per RULES.md retention policy.
"""

from __future__ import annotations

import asyncio

import click

from bioetl.composition.entrypoints import get_bronze_cleanup_service
from bioetl.interfaces.cli.formatters import (
    echo_dry_run_prefix,
    echo_info,
    format_bytes,
)


@click.command("bronze-cleanup")
@click.option(
    "-r",
    "--retention-days",
    default=90,
    help="Remove files older than N days",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed",
)
def bronze_cleanup_command(retention_days: int, dry_run: bool) -> None:
    """Clean up old Bronze files (RULES.md 2.1 retention, default 90 days).

    Examples:

        bioetl maintenance bronze-cleanup

        bioetl maintenance bronze-cleanup --dry-run

        bioetl maintenance bronze-cleanup -r 30
    """
    service = get_bronze_cleanup_service()

    async def _run() -> None:
        if dry_run:
            echo_dry_run_prefix(
                f"Cleanup Bronze files older than {retention_days} days"
            )
        result = await service.cleanup(retention_days=retention_days, dry_run=dry_run)
        action = "Would remove" if dry_run else "Removed"
        echo_info(
            f"{action} {result.files_removed} files ({format_bytes(result.bytes_freed)})"
        )
        echo_info(f"{action} {result.directories_removed} empty directories")

    asyncio.run(_run())
