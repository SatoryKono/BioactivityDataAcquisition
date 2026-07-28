"""Canonical maintenance Click command group (owner domain package).

Ordinary first-party code should import from this module (or
``bioetl.interfaces.cli.commands.domains.maintenance``). The top-level
``bioetl.interfaces.cli.commands.maintenance`` package path remains a
sanctioned external public seam that re-exports this group.
"""

from __future__ import annotations

from importlib import import_module
from typing import cast

import click
from click.core import Group

from bioetl.interfaces.cli.commands.archive import archive_command
from bioetl.interfaces.cli.commands.cleanup import (
    bronze_cleanup_command,
    cleanup_preview_command,
)
from bioetl.interfaces.cli.commands.domains.maintenance.control_plane_lifecycle import (
    control_plane_lifecycle_command,
)
from bioetl.interfaces.cli.commands.domains.shared.click_options import (
    typed_click_group,
)

__all__ = [
    "maintenance",
]

_LAZY_MAINTENANCE_COMMANDS: dict[str, tuple[str, str, str]] = {
    "plan": (
        "bioetl.interfaces.cli.commands.domains.maintenance.plan",
        "plan_command",
        "Plan contract migration actions",
    ),
    # Lazy vacuum loads break the static package→command_group→vacuum→package SCC
    # while preserving the same Click surface for operators.
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
}

_EAGER_MAINTENANCE_COMMANDS: dict[str, tuple[click.Command | click.Group, str]] = {
    "archive": (cast(click.Command, archive_command), "Archive a Delta table"),
    "bronze-cleanup": (
        cast(click.Command, bronze_cleanup_command),
        "Remove expired Bronze artifacts",
    ),
    "cleanup-preview": (
        cast(click.Command, cleanup_preview_command),
        "Preview pipeline cleanup scope",
    ),
    "control-plane-lifecycle": (
        cast(click.Command, control_plane_lifecycle_command),
        "Plan/apply control-plane artifact cleanup",
    ),
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


def _configure_lazy_maintenance_group(group: Group) -> Group:
    """Attach lazy command resolution to the maintenance Click group."""

    def list_commands(ctx: click.Context) -> list[str]:
        del ctx
        return [*_EAGER_MAINTENANCE_COMMANDS, *_LAZY_MAINTENANCE_COMMANDS]

    def get_command(
        ctx: click.Context,
        cmd_name: str,
    ) -> click.Command | click.Group | None:
        del ctx
        if cmd_name in group.commands:
            return group.commands[cmd_name]
        command = _load_maintenance_command(cmd_name)
        if command is not None:
            group.commands[cmd_name] = command
        return command

    def format_commands(
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

    group.list_commands = list_commands  # type: ignore[method-assign]
    group.get_command = get_command  # type: ignore[method-assign]
    group.format_commands = format_commands  # type: ignore[method-assign]
    return group


@typed_click_group()
def _maintenance_group() -> None:
    """Maintenance operations for Delta tables."""


maintenance: Group = _configure_lazy_maintenance_group(cast(Group, _maintenance_group))
