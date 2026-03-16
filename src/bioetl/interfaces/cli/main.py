"""Main CLI entry point for BioETL.

This module provides the main Click group and registers all command groups.
It serves as the thin orchestration layer that delegates to Application services.
"""

from __future__ import annotations

import click

from bioetl.domain.version import get_version
from bioetl.interfaces.cli.commands.adr import adr
from bioetl.interfaces.cli.commands.checkpoint import checkpoint
from bioetl.interfaces.cli.commands.config import config
from bioetl.interfaces.cli.commands.debug import debug
from bioetl.interfaces.cli.commands.export import export_command
from bioetl.interfaces.cli.commands.health import health
from bioetl.interfaces.cli.commands.lock import lock
from bioetl.interfaces.cli.commands.maintenance import maintenance
from bioetl.interfaces.cli.commands.quarantine import quarantine
from bioetl.interfaces.cli.commands.run import run
from bioetl.interfaces.cli.commands.run_all import run_all
from bioetl.interfaces.cli.commands.run_composite import run_composite
from bioetl.interfaces.cli.registry_helpers import (
    _build_registered_registry,
    create_registry,
    get_default_registry,
    register_all_pipelines,
)

__all__ = [
    "cli",
    "main",
]


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


@click.group()
@click.version_option(version=get_version())
@click.pass_context
def cli(ctx: click.Context) -> None:
    """BioETL - Bioactivity Data ETL Pipeline."""
    if ctx.obj is None:
        ctx.obj = get_default_registry()


# Register commands
cli.add_command(run)
cli.add_command(run_all)
cli.add_command(run_composite)
cli.add_command(adr)
cli.add_command(export_command, name="export")
cli.add_command(quarantine)
cli.add_command(checkpoint)
cli.add_command(config)
cli.add_command(debug)
cli.add_command(health)
cli.add_command(lock)
cli.add_command(maintenance)


def main() -> None:
    """Main entry point."""
    cli(obj=_build_main_registry())


if __name__ == "__main__":
    main()
