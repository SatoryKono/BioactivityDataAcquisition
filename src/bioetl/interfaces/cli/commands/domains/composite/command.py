"""Internal wrapper for the public run-composite command module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.run_composite import (
    bootstrap_composite_runner,
    load_composite_config,
    run_composite,
)

__all__ = [
    "bootstrap_composite_runner",
    "load_composite_config",
    "run_composite",
]
