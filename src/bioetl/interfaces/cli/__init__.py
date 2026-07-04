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

from importlib import import_module

_main_module = import_module("bioetl.interfaces.cli.main")
cli = _main_module.cli


def _main_entrypoint() -> None:
    """Invoke the canonical CLI entry point."""
    _impl = _main_module.main

    _impl()


main = _main_entrypoint


def __dir__() -> list[str]:
    """Return stable CLI exports for introspection."""
    return sorted(set(globals()) | set(__all__))


__all__ = [
    "cli",
    "main",
]
