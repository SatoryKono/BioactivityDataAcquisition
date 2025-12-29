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

# Re-export helper functions for backward compatibility with tests
from bioetl.interfaces.cli.commands.run import (
    _get_runner_logger,
    _handle_destructive_run_confirmation,
    validate_pipeline_name,
)
from bioetl.interfaces.cli.main import cli, main

__all__ = [
    "_get_runner_logger",
    "_handle_destructive_run_confirmation",
    "cli",
    "main",
    "validate_pipeline_name",
]
