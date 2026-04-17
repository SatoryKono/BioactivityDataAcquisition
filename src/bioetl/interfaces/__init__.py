"""User interfaces for BioETL.

This package contains user-facing interfaces for the BioETL system.
Currently provides CLI and observability interfaces.

Components:
    cli: Command-line interface (Click-based).
    observability: User-facing observability utilities.

The interfaces layer sits at the outermost ring of the hexagonal
architecture and depends on all other layers per RULES.md.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

_LAZY_MODULE_EXPORTS: dict[str, str] = {
    "cli": "bioetl.interfaces.cli",
    "http": "bioetl.interfaces.http",
    "observability": "bioetl.interfaces.observability",
}

__all__ = list(_LAZY_MODULE_EXPORTS.keys())


def __getattr__(name: str) -> ModuleType:
    """Lazily expose interface subpackages for patch/import stability."""
    try:
        module_name = _LAZY_MODULE_EXPORTS[name]
    except KeyError as exc:  # pragma: no cover - standard attribute path
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = import_module(module_name)
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    """Return stable interface exports for shell/help introspection."""
    return sorted(set(globals()) | set(__all__))
