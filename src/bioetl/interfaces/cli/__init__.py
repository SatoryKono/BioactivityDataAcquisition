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

from collections.abc import Callable
from importlib import import_module
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_runner_models import RunOptions
    from bioetl.domain.ports import ExecutionMetricsRunnerPort


def create_pipeline_runner(
    name: str,
    options: RunOptions,
) -> ExecutionMetricsRunnerPort:
    """Build a pipeline runner via the public composition facade.

    Kept as a package-level convenience export while avoiding a direct
    composition import at module import time.
    """
    from bioetl.composition.execution_api import create_pipeline_runner as _impl

    impl = cast("Callable[[str, RunOptions], ExecutionMetricsRunnerPort]", _impl)
    return impl(name, options)


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
    "create_pipeline_runner",
    "main",
    "validate_pipeline_name",
]

_PUBLIC_EXPORTS = {
    "validate_pipeline_name": (
        "bioetl.interfaces.cli.commands.domains.run.support",
        "validate_pipeline_name",
    ),
}


def __getattr__(name: str) -> object:
    """Resolve CLI convenience exports lazily to avoid cross-command fan-out."""
    spec = _PUBLIC_EXPORTS.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = spec
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
