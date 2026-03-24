"""Compatibility shim for canonical pipeline creation wiring symbols.

Sanctioned support seam:
    bioetl.composition.factories.pipeline.creation_support

Private owner:
    bioetl.composition.factories.pipeline._creation_wiring
"""

from __future__ import annotations

from bioetl.composition.factories.pipeline import creation_support as _creation_support

__all__ = list(_creation_support.__all__)


def __getattr__(name: str) -> object:
    """Delegate sanctioned compatibility exports through creation_support."""
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(_creation_support, name)
