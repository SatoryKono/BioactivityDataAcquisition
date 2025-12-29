"""Quarantine management commands for BioETL CLI.

Implements quarantine inspection and management commands.
"""

from __future__ import annotations

import asyncio

import click

from bioetl.composition.entrypoints import get_quarantine_manager
from bioetl.interfaces.cli.formatters import echo_info, echo_quarantine_record


@click.group()
def quarantine() -> None:
    """Manage quarantine (failed records)."""
    pass


@quarantine.command("inspect")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option("--limit", type=int, default=100, help="Maximum records to show")
def quarantine_inspect(pipeline: str, limit: int) -> None:
    """Inspect quarantined records."""
    echo_info(f"Inspecting quarantine for {pipeline} (limit {limit})...")

    quarantine_manager = get_quarantine_manager(pipeline)

    async def _inspect() -> None:
        records = await quarantine_manager.inspect(limit=limit)
        if not records:
            echo_info("No records found.")
            return

        for rec in records:
            echo_quarantine_record(rec)

    asyncio.run(_inspect())
