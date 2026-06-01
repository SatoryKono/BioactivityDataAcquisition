"""Maintenance command group for BioETL CLI.

Registers all maintenance-related subcommands for Delta table operations.
This module keeps subcommand imports lazy so ``maintenance --help`` stays cheap.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from importlib import import_module
from typing import TYPE_CHECKING, cast

import click

__all__ = [
    "maintenance",
]

if TYPE_CHECKING:
    from bioetl.application.core.lifecycle.cleanup_service import CleanupPreview
    from bioetl.application.services.bronze_cleanup_service import (
        BronzeCleanupService,
    )
    from bioetl.application.services.contract_migration_service import (
        ContractMigrationService,
    )
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.application.services.vacuum_service import VacuumService

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


def get_lifecycle_service() -> MedallionLifecycleService:
    """Load the lifecycle service through composition on demand."""
    from bioetl.composition.maintenance_api import get_lifecycle_service as _impl

    return _impl()


def get_vacuum_service() -> VacuumService:
    """Load the vacuum service through composition on demand."""
    from bioetl.composition.maintenance_api import get_vacuum_service as _impl

    return _impl()


def get_bronze_cleanup_service() -> BronzeCleanupService:
    """Load the bronze cleanup service through composition on demand."""
    from bioetl.composition.maintenance_api import (
        get_bronze_cleanup_service as _impl,
    )

    return _impl()


def get_contract_migration_service() -> ContractMigrationService:
    """Load the contract migration service through composition on demand."""
    from bioetl.composition.maintenance_api import (
        get_contract_migration_service as _impl,
    )

    return _impl()


async def preview_cleanup(pipeline: str) -> CleanupPreview:
    """Preview pipeline cleanup through the maintenance composition seam."""
    from bioetl.composition.maintenance_api import preview_cleanup as _impl

    impl = cast("Callable[[str], Awaitable[CleanupPreview]]", _impl)
    return await impl(pipeline)


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
