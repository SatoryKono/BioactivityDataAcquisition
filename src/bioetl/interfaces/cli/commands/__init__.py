"""CLI commands package for BioETL.

The sanctioned public CLI surface remains at ``bioetl.interfaces.cli.commands.*``,
while canonical implementations are partitioned by operational domain under
``bioetl.interfaces.cli.commands.domains``.
"""

from __future__ import annotations

import sys
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

_HELPER_ONLY_MODULES = frozenset({"export_support", "inspection_output"})

__all__ = sorted(_PUBLIC_COMMAND_MODULES)


class _CommandsModule(ModuleType):
    """Hide helper-only submodules even if import machinery binds them locally."""

    def __getattribute__(self, name: str) -> object:
        if name in _HELPER_ONLY_MODULES:
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
        return super().__getattribute__(name)


def __getattr__(name: str) -> ModuleType:
    """Lazily expose retained top-level command seams for compat patch targets."""
    if name not in _PUBLIC_COMMAND_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module


sys.modules[__name__].__class__ = _CommandsModule
