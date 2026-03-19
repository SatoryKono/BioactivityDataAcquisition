"""Thin wrapper re-exporting canonical run-composite helpers."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.domains.composite.helpers import (
    emit_composite_startup,
    exit_with_composite_result,
    handle_run_composite_exception,
    run_composite_with_cli_policy,
)

__all__ = [
    "emit_composite_startup",
    "exit_with_composite_result",
    "handle_run_composite_exception",
    "run_composite_with_cli_policy",
]
