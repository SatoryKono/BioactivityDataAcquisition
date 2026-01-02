"""Main CLI entry point for BioETL.

This module provides the main Click group and registers all command groups.
It serves as the thin orchestration layer that delegates to Application services.
"""

from __future__ import annotations

import click

from bioetl import __version__
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.interfaces.cli.commands.checkpoint import checkpoint
from bioetl.interfaces.cli.commands.config import config
from bioetl.interfaces.cli.commands.health import health
from bioetl.interfaces.cli.commands.lock import lock
from bioetl.interfaces.cli.commands.maintenance import maintenance
from bioetl.interfaces.cli.commands.quarantine import quarantine
from bioetl.interfaces.cli.commands.run import run
from bioetl.interfaces.cli.commands.run_all import run_all


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """BioETL - Bioactivity Data ETL Pipeline."""
    pass


# Register commands
cli.add_command(run)
cli.add_command(run_all)
cli.add_command(quarantine)
cli.add_command(checkpoint)
cli.add_command(config)
cli.add_command(health)
cli.add_command(lock)
cli.add_command(maintenance)


def main() -> None:
    """Main entry point."""
    register_all_pipelines()
    cli()


if __name__ == "__main__":
    main()
