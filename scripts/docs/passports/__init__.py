"""Deterministic documentation projections for BioETL executable units."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .projector import build_all_outputs, check_outputs, write_outputs

__all__ = ["build_all_outputs", "check_outputs", "write_outputs"]


def __getattr__(name: str) -> Any:
    """Load the heavyweight projector only when its public API is requested."""
    if name not in __all__:
        raise AttributeError(name)
    from . import projector

    return getattr(projector, name)
