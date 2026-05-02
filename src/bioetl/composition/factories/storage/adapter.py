"""Deprecated compatibility shim for the storage bundle module.

Use ``bioetl.composition.factories.storage.bundle.StorageBundle`` instead.
Removal horizon: 2026-09-30 compatibility facade review.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.composition.factories.storage.bundle import StorageBundle

__all__ = ["StorageBundle"]


def __getattr__(name: str) -> Any:  # Any: module-level deprecated export shim
    """Resolve deprecated storage bundle exports lazily."""
    if name != "StorageBundle":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from bioetl.composition.factories.storage.bundle import StorageBundle

    warnings.warn(
        (
            "`bioetl.composition.factories.storage.adapter.StorageBundle` is "
            "deprecated; import `StorageBundle` from "
            "`bioetl.composition.factories.storage.bundle` instead."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    globals()[name] = StorageBundle
    return StorageBundle
