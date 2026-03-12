"""Canonical storage factory module.

Provides the storage context factory and related writer patch points.
The legacy ``factory`` module remains for backward compatibility.
"""

from __future__ import annotations

from bioetl.composition.factories.storage.factory import (
    BronzeWriter,
    GoldWriter,
    SilverWriter,
    StorageContext,
    StorageFactory,
)

__all__ = [
    "BronzeWriter",
    "GoldWriter",
    "SilverWriter",
    "StorageContext",
    "StorageFactory",
]
