"""CLI commands package for BioETL.

The sanctioned public CLI surface remains at ``bioetl.interfaces.cli.commands.*``,
while canonical implementations are partitioned by operational domain under
``bioetl.interfaces.cli.commands.domains``.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

_PUBLIC_COMMAND_MODULES = frozenset(
    {
        "adr",
        "archive",
        "checkpoint",
        "cleanup",
        "config",
        "config_dq",
        "diagnostics",
        "debug",
        "export",
        "health",
        "lineage",
        "lock",
        "maintenance",
        "quarantine",
        "run",
        "run_all",
        "run_composite",
        "run_manifest",
        "vacuum",
        "workflow",
    }
)

__all__ = sorted(_PUBLIC_COMMAND_MODULES)


def __getattr__(name: str) -> ModuleType:
    """Lazily expose retained top-level command seams for compat patch targets."""
    if name not in _PUBLIC_COMMAND_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module
