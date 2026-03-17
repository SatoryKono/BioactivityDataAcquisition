"""Checkpoint management commands for BioETL CLI.

Implements checkpoint listing and management commands.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.formatters import echo_checkpoint, echo_info

if TYPE_CHECKING:
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointManagerService,
    )

__all__ = [
    "COMMANDS",
    "checkpoint",
    "checkpoint_list",
]


@click.group()
def checkpoint() -> None:
    """Manage checkpoints."""


def get_checkpoint_manager(pipeline: str) -> CheckpointManagerService:
    """Load the checkpoint manager through composition on demand."""
    from bioetl.composition.resources_api import get_checkpoint_manager as _impl

    return _impl(pipeline)


@checkpoint.command("list")
@click.option("--pipeline", required=True, help="Pipeline name")
def checkpoint_list(pipeline: str) -> None:
    """List all checkpoints.

    Args:
        pipeline: Pipeline.
    """
    echo_info(f"Listing checkpoints for {pipeline}...")

    checkpoint_manager = get_checkpoint_manager(pipeline)

    async def _list() -> None:
        checkpoints = await checkpoint_manager.list_all()
        for cp in checkpoints:
            echo_checkpoint(cp)

    asyncio.run(_list())


# Hint for tooling: explicit reference to command function.
COMMANDS = (checkpoint_list,)
