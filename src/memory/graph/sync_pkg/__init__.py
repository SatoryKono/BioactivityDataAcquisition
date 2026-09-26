# pyright: reportImportCycles=false
"""Responsibility-focused import surface for graph sync.

Re-exports resolve lazily through :mod:`_core` and :mod:`cli` so this package
keeps an explicit ``__all__`` without a star import (AUD-008). ``__all__``
composition is unchanged: every ``_core`` export plus ``cli``-only extras.
"""

from __future__ import annotations

from typing import Any

from memory.graph.sync_pkg import _core as _core_mod
from memory.graph.sync_pkg import cli as _cli_mod

__all__ = [*_core_mod.__all__]
for _name in _cli_mod.__all__:
    if _name not in __all__:
        __all__.append(_name)

_CORE_EXPORTS = frozenset(_core_mod.__all__)
_CLI_EXPORTS = frozenset(_cli_mod.__all__)

# Package file build_snapshot.py must not hide the callable _core export.
build_snapshot = _core_mod.build_snapshot


def __getattr__(name: str) -> Any:
    if name in _CORE_EXPORTS:
        return getattr(_core_mod, name)
    if name in _CLI_EXPORTS:
        return getattr(_cli_mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
