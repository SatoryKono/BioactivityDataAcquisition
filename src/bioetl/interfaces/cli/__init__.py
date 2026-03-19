"""CLI package for BioETL.

Provides command-line interface for pipeline operations.
This package follows the thin controller pattern - commands delegate
to Application services for all business logic.

Structure:
    cli/
    ├── __init__.py      # Package exports
    ├── main.py          # CLI entry point
    ├── formatters.py    # Output formatters
    └── commands/        # Individual command modules
        ├── run.py       # bioetl run
        ├── checkpoint.py# bioetl checkpoint
        ├── quarantine.py# bioetl quarantine
        └── maintenance.py# bioetl maintenance
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands.domains.run.support import validate_pipeline_name
from bioetl.interfaces.cli.main import cli, main
from bioetl.interfaces.cli.registry_helpers import build_cli_registry

if TYPE_CHECKING:
    from bioetl.application.services import RunOptions
    from bioetl.domain.ports import ExecutionMetricsRunnerPort

# Backward-compatible package export kept while canonical helper is build_cli_registry().
get_default_registry = build_cli_registry


def create_pipeline_runner(
    name: str,
    options: RunOptions,
) -> ExecutionMetricsRunnerPort:
    """Build a pipeline runner via the public composition facade.

    Kept as a package-level convenience export while avoiding a direct
    composition import at module import time.
    """
    from bioetl.composition.execution_api import create_pipeline_runner as _impl

    return _impl(name, options)


__all__ = [
    "cli",
    "create_pipeline_runner",
    "get_default_registry",
    "main",
    "validate_pipeline_name",
]
