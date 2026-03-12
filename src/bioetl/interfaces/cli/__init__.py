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

# Re-export entrypoint functions for convenience
from bioetl.composition.entrypoints import create_pipeline_runner
from bioetl.interfaces.cli.commands.run_helpers import validate_pipeline_name
from bioetl.interfaces.cli.main import cli, main
from bioetl.interfaces.cli.registry_helpers import get_default_registry

__all__ = [
    "cli",
    "create_pipeline_runner",
    "get_default_registry",
    "main",
    "validate_pipeline_name",
]
