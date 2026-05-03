"""Internal wrapper for the public run-all command module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.run_all import (
    _run_batch_with_policy,
    get_pipeline_runner_service,
    resolve_context_registry,
    run_all,
)

__all__ = ["get_pipeline_runner_service", "run_all"]
