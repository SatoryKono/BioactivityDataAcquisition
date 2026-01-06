"""Checkpoint management commands for BioETL CLI.

Implements checkpoint listing and management commands.
"""

from __future__ import annotations

import asyncio

import click

from bioetl.composition.entrypoints import get_checkpoint_manager
from bioetl.interfaces.cli.formatters import echo_checkpoint, echo_info


@click.group()
def checkpoint() -> None:
    """Manage checkpoints."""


@checkpoint.command("list")
@click.option("--pipeline", required=True, help="Pipeline name")
def checkpoint_list(pipeline: str) -> None:
    """List all checkpoints."""
    echo_info(f"Listing checkpoints for {pipeline}...")

    checkpoint_manager = get_checkpoint_manager(pipeline)

    async def _list() -> None:
        checkpoints = await checkpoint_manager.list_all()
        for cp in checkpoints:
            echo_checkpoint(cp)

    asyncio.run(_list())
