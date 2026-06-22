"""Runtime bootstrap module for pipeline execution.

Contains bootstrap functions for actual pipeline execution scenarios:
- Single pipeline runs (incremental, backfill, rebuild)
- Composite pipeline runs with enrichment coordination
- Full observability stack (logging, tracing, metrics, DQ monitoring)

IMPORTANT: This module MUST NOT import from bootstrap/cli/.
CLI modules may import from runtime for runner access, but not vice versa.

Public runtime helpers are re-exported lazily so importing one light-weight
submodule does not eagerly initialize the full runtime bootstrap graph.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from bioetl.composition.bootstrap._runtime_public_exports import (
    RUNTIME_PACKAGE_EXPORT_NAMES,
    RUNTIME_PACKAGE_PUBLIC_EXPORTS,
)

_RUNTIME_MODULE_EXPORTS: dict[str, str] = {
    "composite_control_plane_builder": (
        "bioetl.composition.bootstrap.runtime.composite_control_plane_builder"
    ),
}

__all__ = list(RUNTIME_PACKAGE_EXPORT_NAMES)

_PUBLIC_EXPORTS: dict[str, str] = RUNTIME_PACKAGE_PUBLIC_EXPORTS


def __getattr__(
    name: str,
) -> (
    Any  # Any: lazy runtime re-export preserves the original symbol type at lookup time.
):  # Any: lazy runtime re-export preserves the original symbol type at lookup time.
    """Resolve runtime re-exports lazily to keep package import light-weight."""
    module_name = _RUNTIME_MODULE_EXPORTS.get(name)
    if module_name is not None:
        module = import_module(module_name)
        globals()[name] = module
        return module
    export_module_name = _PUBLIC_EXPORTS.get(name)
    if export_module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(export_module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy re-exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))
