"""Maintenance command group for BioETL CLI.

Registers all maintenance-related subcommands for Delta table operations.
This module keeps subcommand imports lazy so ``maintenance --help`` stays cheap.
"""

from __future__ import annotations

from importlib import import_module

import click

from bioetl.interfaces.cli.commands.domains.maintenance.service_access import (
    get_bronze_cleanup_service,
    get_contract_migration_service,
    get_lifecycle_service,
    get_vacuum_service,
    preview_cleanup,
)

__all__ = [
    "get_bronze_cleanup_service",
    "get_contract_migration_service",
    "get_lifecycle_service",
    "get_vacuum_service",
    "maintenance",
    "preview_cleanup",
]

_LAZY_MAINTENANCE_COMMANDS: dict[str, tuple[str, str, str]] = {
    "vacuum": (
        "bioetl.interfaces.cli.commands.vacuum",
        "vacuum_command",
        "Vacuum one Delta table",
    ),
    "vacuum-all": (
        "bioetl.interfaces.cli.commands.vacuum",
        "vacuum_all_command",
        "Vacuum multiple Delta tables",
    ),
    "archive": (
        "bioetl.interfaces.cli.commands.archive",
        "archive_command",
        "Archive a Delta table",
    ),
    "bronze-cleanup": (
        "bioetl.interfaces.cli.commands.cleanup",
        "bronze_cleanup_command",
        "Remove expired Bronze artifacts",
    ),
    "cleanup-preview": (
        "bioetl.interfaces.cli.commands.cleanup",
        "cleanup_preview_command",
        "Preview pipeline cleanup scope",
    ),
    "control-plane-lifecycle": (
        "bioetl.interfaces.cli.commands.domains.maintenance.control_plane_lifecycle",
        "control_plane_lifecycle_command",
        "Plan/apply control-plane artifact cleanup",
    ),
    "plan": (
        "bioetl.interfaces.cli.commands.domains.maintenance.plan",
        "plan_command",
        "Plan contract migration actions",
    ),
}


def _load_maintenance_command(name: str) -> click.Command | click.Group | None:
    """Import one maintenance subcommand only when it is requested."""
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
        return list(_LAZY_MAINTENANCE_COMMANDS)

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
        rows = [
            (name, help_text)
            for name, (_module_name, _attribute_name, help_text) in (
                _LAZY_MAINTENANCE_COMMANDS.items()
            )
        ]
        if rows:
            with formatter.section("Commands"):
                formatter.write_dl(rows)


@click.group(cls=_LazyMaintenanceGroup)
def maintenance() -> None:
    """Maintenance operations for Delta tables."""
