"""Composition-facing seams for application-core assembly.

This package groups the stable wiring APIs used by ``composition/`` while
avoiding eager imports of the entire wiring surface during package
initialization. Static re-export declarations live in the adjacent stub.
"""

from __future__ import annotations

from importlib import import_module

_WIRING_SUBMODULES = (
    "bioetl.application.core.wiring.factory",
    "bioetl.application.core.wiring.registry",
    "bioetl.application.core.wiring.runtime",
    "bioetl.application.core.wiring.transformer",
)


def _build_export_groups() -> dict[str, tuple[str, ...]]:
    return {
        module_name: tuple(import_module(module_name).__all__)
        for module_name in _WIRING_SUBMODULES
    }


_EXPORT_GROUPS = _build_export_groups()
_EXPORT_MODULES = {
    export_name: module_name
    for module_name, export_names in _EXPORT_GROUPS.items()
    for export_name in export_names
}
__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str) -> object:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
