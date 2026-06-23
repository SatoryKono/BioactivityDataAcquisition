"""Lazy package exports for memory tooling submodules.

The tooling package is used in two distinct ways:

- direct submodule execution, e.g. ``python -m memory.tooling.workflow``
- attribute-style imports, e.g. ``from memory.tooling import workflow``

Eagerly importing every submodule here makes both paths fragile because
``memory.query`` imports ``memory.tooling.refresh_all`` while
``memory.tooling.workflow`` imports ``memory.query``. Running the workflow
module with ``-m`` then loads the target module via package import first and
triggers a partially initialized circular import plus a ``runpy`` warning.

Expose the same attribute API via lazy imports instead of importing submodules
at package import time.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

_SUBMODULES = {
    "archive_note",
    "create_note",
    "promote_note",
    "prune",
    "refresh_all",
    "review_curated",
    "validate",
    "workflow",
}

__all__ = sorted(_SUBMODULES)


def __getattr__(name: str) -> ModuleType:
    """Resolve tooling submodules lazily for attribute-style imports."""
    if name not in _SUBMODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    """Keep interactive inspection aligned with the lazy export surface."""
    return sorted(set(globals()) | _SUBMODULES)
