"""Maintenance command group for BioETL CLI.

Registers all maintenance-related subcommands for Delta table operations.
This module is a thin orchestrator that imports and registers commands.
"""

from __future__ import annotations

import click

from bioetl.interfaces.cli.commands.archive import archive_command
from bioetl.interfaces.cli.commands.cleanup import bronze_cleanup_command
from bioetl.interfaces.cli.commands.vacuum import vacuum_all_command, vacuum_command


@click.group()
def maintenance() -> None:
    """Maintenance operations for Delta tables."""
    pass


# Register all maintenance subcommands
maintenance.add_command(vacuum_command)
maintenance.add_command(vacuum_all_command)
maintenance.add_command(archive_command)
maintenance.add_command(bronze_cleanup_command)
