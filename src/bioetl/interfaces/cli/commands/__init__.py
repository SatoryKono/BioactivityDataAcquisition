"""CLI commands package for BioETL.

The sanctioned public CLI surface remains at ``bioetl.interfaces.cli.commands.*``,
while canonical implementations are partitioned by operational domain under
``bioetl.interfaces.cli.commands.domains``.
"""

from __future__ import annotations

import sys
from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands import adr as adr
    from bioetl.interfaces.cli.commands import archive as archive
    from bioetl.interfaces.cli.commands import checkpoint as checkpoint
    from bioetl.interfaces.cli.commands import cleanup as cleanup
    from bioetl.interfaces.cli.commands import config as config
    from bioetl.interfaces.cli.commands import config_dq as config_dq
    from bioetl.interfaces.cli.commands import debug as debug
    from bioetl.interfaces.cli.commands import diagnostics as diagnostics
    from bioetl.interfaces.cli.commands import export as export
    from bioetl.interfaces.cli.commands import health as health
    from bioetl.interfaces.cli.commands import lineage as lineage
    from bioetl.interfaces.cli.commands import lock as lock
    from bioetl.interfaces.cli.commands import maintenance as maintenance
    from bioetl.interfaces.cli.commands import quarantine as quarantine
    from bioetl.interfaces.cli.commands import run as run
    from bioetl.interfaces.cli.commands import run_all as run_all
    from bioetl.interfaces.cli.commands import run_composite as run_composite
    from bioetl.interfaces.cli.commands import run_manifest as run_manifest
    from bioetl.interfaces.cli.commands import vacuum as vacuum
    from bioetl.interfaces.cli.commands import workflow as workflow

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

    return import_module(f"{__name__}.{name}")


sys.modules[__name__].__class__ = _CommandsModule
