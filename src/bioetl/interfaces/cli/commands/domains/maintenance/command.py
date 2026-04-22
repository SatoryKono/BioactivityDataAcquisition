"""Maintenance command group for BioETL CLI.

Registers all maintenance-related subcommands for Delta table operations.
This module is a thin orchestrator that imports and registers commands.
"""

from __future__ import annotations

import click

from bioetl.interfaces.cli.commands.domains.maintenance.archive import archive_command
from bioetl.interfaces.cli.commands.domains.maintenance.cleanup import (
    bronze_cleanup_command,
    cleanup_preview_command,
)
from bioetl.interfaces.cli.commands.domains.maintenance.control_plane_lifecycle import (
    control_plane_lifecycle_command,
)
from bioetl.interfaces.cli.commands.domains.maintenance.plan import plan_command
from bioetl.interfaces.cli.commands.domains.maintenance.vacuum import (
    vacuum_all_command,
    vacuum_command,
)

__all__ = [
    "maintenance",
]


@click.group()  # type: ignore[untyped-decorator]
def maintenance() -> None:
    """Maintenance operations for Delta tables."""


# Register all maintenance subcommands
maintenance.add_command(vacuum_command)
maintenance.add_command(vacuum_all_command)
maintenance.add_command(archive_command)
maintenance.add_command(bronze_cleanup_command)
maintenance.add_command(cleanup_preview_command)
maintenance.add_command(control_plane_lifecycle_command)
maintenance.add_command(plan_command)
