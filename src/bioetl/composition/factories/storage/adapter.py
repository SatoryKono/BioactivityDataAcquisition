"""Deprecated compatibility shim for storage bundle imports.

Canonical code lives in ``bioetl.composition.factories.storage.bundle``.
This reviewed shim is retained only for callers that still import the old
``adapter`` path during the 2026-09-30 transition window.
"""

from __future__ import annotations

from warnings import warn

from bioetl.composition.factories.storage.bundle import StorageBundle

warn(
    "bioetl.composition.factories.storage.adapter is deprecated; "
    "import StorageBundle from bioetl.composition.factories.storage.bundle. "
    "This compatibility path is scheduled for removal after 2026-09-30.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["StorageBundle"]
