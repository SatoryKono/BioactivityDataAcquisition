"""Internal wrapper for the public run-all command module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.run_all import (
    get_pipeline_runner_service,
    run_all,
)

__all__ = ["get_pipeline_runner_service", "run_all"]
