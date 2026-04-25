"""Main CLI entry point for BioETL.

This module provides the main Click group and registers command groups lazily.
It keeps import-time overhead low for targeted CLI tests and single-command use.
"""

from __future__ import annotations

import sys
from importlib import import_module
from types import ModuleType

import click
from click.core import Command, Context, Group
from click.formatting import HelpFormatter

from bioetl import __version__ as BIOETL_VERSION
from bioetl.interfaces.cli.registry_helpers import (
    _build_registered_registry,
    create_registry,
    register_all_pipelines,
)

__all__ = [
    "build_cli_registry",
    "cli",
    "main",
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
}


def _load_cli_command(command_name: str) -> Command | Group | None:
    """Import a CLI command module only when the command is requested."""
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


class _LazyCliGroup(Group):
    """Click group that resolves BioETL subcommands on demand."""

    def list_commands(self, ctx: Context) -> list[str]:
        del ctx
        return list(_LAZY_COMMAND_SPECS)

    def get_command(
        self,
        ctx: Context,
        cmd_name: str,
    ) -> Command | Group | None:
        del ctx
        if cmd_name in self.commands:
            return self.commands[cmd_name]

        command = _load_cli_command(cmd_name)
        if command is not None:
            self.commands[cmd_name] = command
        return command

    def format_commands(
        self,
        ctx: Context,
        formatter: HelpFormatter,
    ) -> None:
        del ctx
        rows = [
            (name, help_text)
            for name, (_module_name, _attribute_name, help_text) in (
                _LAZY_COMMAND_SPECS.items()
            )
        ]
        if rows:
            with formatter.section("Commands"):
                formatter.write_dl(rows)


def _build_main_registry() -> object:
    """Build an explicit registry for the canonical process entrypoint.

    Uses interface-layer registry helpers so the CLI entry module does not
    import composition modules directly while preserving historical patch
    points used by tests.
    """
    return _build_registered_registry(
        create_registry_fn=create_registry,
        register_all_pipelines_fn=register_all_pipelines,
    )


def build_cli_registry() -> object:
    """Compatibility seam retaining the historical main-level registry builder."""
    return _build_main_registry()


@click.group(cls=_LazyCliGroup)
@click.version_option(version=BIOETL_VERSION)
@click.pass_context
def cli(ctx: Context) -> None:
    """BioETL - Bioactivity Data ETL Pipeline."""
    del ctx


def main() -> None:
    """Main entry point."""
    cli()


class _CallableCliMainModule(ModuleType):
    """Allow `from bioetl.interfaces.cli import main` to remain callable."""

    def __call__(self) -> None:
        main()


sys.modules[__name__].__class__ = _CallableCliMainModule


if __name__ == "__main__":
    main()
