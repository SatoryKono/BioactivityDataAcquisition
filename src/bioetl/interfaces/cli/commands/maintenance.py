"""Maintenance command group for BioETL CLI.

Registers all maintenance-related subcommands for Delta table operations.
This module keeps subcommand imports lazy so ``maintenance --help`` stays cheap.
"""

from __future__ import annotations

from importlib import import_module

import click

from bioetl.interfaces.cli.commands.archive import archive_command
from bioetl.interfaces.cli.commands.cleanup import (
    bronze_cleanup_command,
    cleanup_preview_command,
)
from bioetl.interfaces.cli.commands.domains.maintenance.control_plane_lifecycle import (
    control_plane_lifecycle_command,
)
from bioetl.interfaces.cli.commands.domains.maintenance.service_access import (
    get_bronze_cleanup_service,
    get_contract_migration_service,
    get_lifecycle_service,
    get_vacuum_service,
    preview_cleanup,
)
from bioetl.interfaces.cli.commands.vacuum import vacuum_all_command, vacuum_command

__all__ = [
    "get_bronze_cleanup_service",
    "get_contract_migration_service",
    "get_lifecycle_service",
    "get_vacuum_service",
    "maintenance",
    "preview_cleanup",
]

_LAZY_MAINTENANCE_COMMANDS: dict[str, tuple[str, str, str]] = {
    "plan": (
        "bioetl.interfaces.cli.commands.domains.maintenance.plan",
        "plan_command",
        "Plan contract migration actions",
    ),
}

_EAGER_MAINTENANCE_COMMANDS: dict[str, tuple[click.Command | click.Group, str]] = {
    "archive": (archive_command, "Archive a Delta table"),
    "bronze-cleanup": (bronze_cleanup_command, "Remove expired Bronze artifacts"),
    "cleanup-preview": (
        cleanup_preview_command,
        "Preview pipeline cleanup scope",
    ),
    "control-plane-lifecycle": (
        control_plane_lifecycle_command,
        "Plan/apply control-plane artifact cleanup",
    ),
    "vacuum": (vacuum_command, "Vacuum one Delta table"),
    "vacuum-all": (vacuum_all_command, "Vacuum multiple Delta tables"),
}


def _load_maintenance_command(name: str) -> click.Command | click.Group | None:
    """Import one maintenance subcommand only when it is requested."""
    eager_spec = _EAGER_MAINTENANCE_COMMANDS.get(name)
    if eager_spec is not None:
        command, _help_text = eager_spec
        if getattr(command, "name", name) != name:
            command.name = name
        return command

    spec = _LAZY_MAINTENANCE_COMMANDS.get(name)
    if spec is None:
        return None
    module_name, attribute_name, _help_text = spec
    command = getattr(import_module(module_name), attribute_name)
    if not isinstance(command, click.Command):
        raise TypeError(
            f"{module_name}.{attribute_name} must resolve to a Click command"
        )
    if getattr(command, "name", name) != name:
        command.name = name
    return command


class _LazyMaintenanceGroup(click.Group):
    """Click group that resolves maintenance subcommands on demand."""

    def list_commands(self, ctx: click.Context) -> list[str]:
        del ctx
        return [*_EAGER_MAINTENANCE_COMMANDS, *_LAZY_MAINTENANCE_COMMANDS]

    def get_command(
        self,
        ctx: click.Context,
        cmd_name: str,
    ) -> click.Command | click.Group | None:
        del ctx
        if cmd_name in self.commands:
            return self.commands[cmd_name]
        command = _load_maintenance_command(cmd_name)
        if command is not None:
            self.commands[cmd_name] = command
        return command

    def format_commands(
        self,
        ctx: click.Context,
        formatter: click.HelpFormatter,
    ) -> None:
        del ctx
        registry_helpers = import_module("bioetl.interfaces.cli.registry_helpers")
        registry_helpers.format_command_help_rows(
            formatter=formatter,
            eager_commands=_EAGER_MAINTENANCE_COMMANDS,
            lazy_commands=_LAZY_MAINTENANCE_COMMANDS,
        )


@click.group(cls=_LazyMaintenanceGroup)
def maintenance() -> None:
    """Maintenance operations for Delta tables."""
