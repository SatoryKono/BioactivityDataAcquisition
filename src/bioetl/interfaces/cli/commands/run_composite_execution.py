"""Compatibility shim for run-composite execution module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.domains.composite.execution import (
    bootstrap_composite_runner,
    build_run_composite_result,
    load_composite_config,
    run_composite_async,
    run_composite_inner,
)

__all__ = [
    "bootstrap_composite_runner",
    "build_run_composite_result",
    "load_composite_config",
    "run_composite_async",
    "run_composite_inner",
]
