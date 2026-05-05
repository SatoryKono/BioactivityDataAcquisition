"""Lazy access to provider-specific publication block exports."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.pipelines.crossref.blocks import (
        _CrossRefAuthorBlock,
        _CrossRefCoreBlock,
        _CrossRefDateBlock,
        _CrossRefJournalBlock,
        _CrossRefMetadataBlock,
    )

_BLOCK_EXPORTS = frozenset(
    {
        "_CrossRefAuthorBlock",
        "_CrossRefCoreBlock",
        "_CrossRefDateBlock",
        "_CrossRefJournalBlock",
        "_CrossRefMetadataBlock",
    }
)


def __getattr__(name: str) -> object:
    if name not in _BLOCK_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module("bioetl.application.pipelines.crossref.blocks")
    return getattr(module, name)


__all__ = [
    "_CrossRefAuthorBlock",
    "_CrossRefCoreBlock",
    "_CrossRefDateBlock",
    "_CrossRefJournalBlock",
    "_CrossRefMetadataBlock",
]
