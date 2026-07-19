"""Main CLI entry point for BioETL.

This module provides the main Click group and registers command groups lazily.
It keeps import-time overhead low for targeted CLI tests and single-command use.
"""

from __future__ import annotations

from importlib import import_module
from typing import cast

from click.core import Command, Context, Group
from click.formatting import HelpFormatter

from bioetl import __version__ as BIOETL_VERSION
from bioetl.interfaces.cli.commands.config_dq import dq as dq_command
from bioetl.interfaces.cli.commands.debug import debug as debug_command
from bioetl.interfaces.cli.commands.domains.shared.click_options import (
    typed_click_group,
    typed_pass_context,
    typed_version_option,
)
from bioetl.interfaces.cli.commands.lock import lock as lock_command
from bioetl.interfaces.cli.registry_helpers import (
    create_registry as _create_registry,
)
from bioetl.interfaces.cli.registry_helpers import (
    format_command_help_rows as _format_command_help_rows,
)
from bioetl.interfaces.cli.registry_helpers import (
    register_all_pipelines as _register_all_pipelines,
)

__all__ = [
    "build_cli_registry",
    "cli",
    "main",
    "register_all_pipelines",
]

_LAZY_COMMAND_SPECS: dict[str, tuple[str, str, str]] = {
    "adr": ("bioetl.interfaces.cli.commands.adr", "adr", "ADR tooling"),
    "checkpoint": (
        "bioetl.interfaces.cli.commands.checkpoint",
        "checkpoint",
        "Manage pipeline checkpoints",
    ),
    "config": (
        "bioetl.interfaces.cli.commands.config",
        "config",
        "Inspect and validate configuration",
    ),
    "dq": (
        "bioetl.interfaces.cli.commands.config_dq",
        "dq",
        "Data quality configuration commands",
    ),
    "diagnostics": (
        "bioetl.interfaces.cli.commands.diagnostics",
        "diagnostics",
        "Unified operator diagnostics across metrics, health, checkpoints, manifests, and quarantine",
    ),
    "debug": (
        "bioetl.interfaces.cli.commands.debug",
        "debug",
        "Run a pipeline with breakpoints",
    ),
    "export": (
        "bioetl.interfaces.cli.commands.export",
        "export_command",
        "Export pipeline artifacts",
    ),
    "health": (
        "bioetl.interfaces.cli.commands.health",
        "health",
        "Health checks and diagnostics",
    ),
    "lineage": (
        "bioetl.interfaces.cli.commands.lineage",
        "lineage",
        "Inspect pipeline lineage",
    ),
    "lock": (
        "bioetl.interfaces.cli.commands.lock",
        "lock",
        "Inspect and manage local runtime locks",
    ),
    "maintenance": (
        "bioetl.interfaces.cli.commands.maintenance",
        "maintenance",
        "Maintenance operations",
    ),
    "quarantine": (
        "bioetl.interfaces.cli.commands.quarantine",
        "quarantine",
        "Manage quarantine records",
    ),
    "run": (
        "bioetl.interfaces.cli.commands.run",
        "run",
        "Run a configured pipeline",
    ),
    "run-all": (
        "bioetl.interfaces.cli.commands.run_all",
        "run_all",
        "Run all configured pipelines",
    ),
    "run-composite": (
        "bioetl.interfaces.cli.commands.run_composite",
        "run_composite",
        "Run a composite pipeline",
    ),
    "run-manifest": (
        "bioetl.interfaces.cli.commands.run_manifest",
        "run_manifest",
        "Inspect run manifests and ledgers",
    ),
    "workflow": (
        "bioetl.interfaces.cli.commands.workflow",
        "workflow",
        "Run and inspect declarative workflows",
    ),
}

_EAGER_COMMANDS: dict[str, tuple[Command | Group, str]] = {
    "dq": (dq_command, "Data quality configuration commands"),
    "debug": (debug_command, "Run a pipeline with breakpoints"),
    "lock": (lock_command, "Inspect and manage local runtime locks"),
}


def _load_cli_command(command_name: str) -> Command | Group | None:
    """Import a CLI command module only when the command is requested."""
    eager_spec = _EAGER_COMMANDS.get(command_name)
    if eager_spec is not None:
        command, _help_text = eager_spec
        if getattr(command, "name", command_name) != command_name:
            command.name = command_name
        return command

    spec = _LAZY_COMMAND_SPECS.get(command_name)
    if spec is None:
        return None

    module_name, attribute_name, _help_text = spec
    command = getattr(import_module(module_name), attribute_name)
    if not isinstance(command, Command):
        raise TypeError(
            f"{module_name}.{attribute_name} must resolve to a Click command"
        )
    if getattr(command, "name", command_name) != command_name:
        command.name = command_name
    return command


def _configure_lazy_cli_group(group: Group) -> Group:
    """Attach lazy command resolution to the root Click group."""

    def list_commands(ctx: Context) -> list[str]:
        del ctx
        return [*_EAGER_COMMANDS, *_LAZY_COMMAND_SPECS]

    def get_command(
        ctx: Context,
        cmd_name: str,
    ) -> Command | Group | None:
        del ctx
        if cmd_name in group.commands:
            return group.commands[cmd_name]

        command = _load_cli_command(cmd_name)
        if command is not None:
            group.commands[cmd_name] = command
        return command

    def format_commands(
        ctx: Context,
        formatter: HelpFormatter,
    ) -> None:
        del ctx
        _format_command_help_rows(
            formatter=formatter,
            eager_commands=_EAGER_COMMANDS,
            lazy_commands=_LAZY_COMMAND_SPECS,
        )

    group.list_commands = list_commands
    group.get_command = get_command
    group.format_commands = format_commands
    return group


def _build_main_registry() -> object:
    """Build an explicit registry for the canonical process entrypoint.

    Uses the canonical interface-layer helper so the process entrypoint and
    runtime commands share one explicit-registry bootstrap path while retaining
    the historical patch seam for CLI unit tests.
    """
    return build_cli_registry()


def register_all_pipelines(*, registry: object | None = None) -> None:
    """Historical CLI patch seam for pipeline registration."""
    _register_all_pipelines(registry=registry)


def build_cli_registry() -> object:
    """Build a fresh CLI registry through local test seams."""
    registry = _create_registry()
    register_all_pipelines(registry=registry)
    return registry


@typed_click_group()
@typed_version_option(version=BIOETL_VERSION)
@typed_pass_context
def _cli_group(ctx: Context) -> None:
    """BioETL - Bioactivity Data ETL Pipeline."""
    del ctx


cli: Group = _configure_lazy_cli_group(cast(Group, _cli_group))


def main() -> None:
    """Main entry point.

    Canonical process startup keeps the top-level Click entrypoint lightweight.
    Commands that actually need a registry resolve or build it lazily through
    the canonical CLI helper path.
    """
    cli(obj=None)


if __name__ == "__main__":
    main()
