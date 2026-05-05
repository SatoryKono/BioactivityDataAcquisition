"""Compatibility re-exports for provider-specific publication blocks."""

from __future__ import annotations

from bioetl.application.pipelines.crossref.blocks import (
    _CrossRefAuthorBlock,
    _CrossRefCoreBlock,
    _CrossRefDateBlock,
    _CrossRefJournalBlock,
    _CrossRefMetadataBlock,
)

__all__ = [
    "_CrossRefAuthorBlock",
    "_CrossRefCoreBlock",
    "_CrossRefDateBlock",
    "_CrossRefJournalBlock",
    "_CrossRefMetadataBlock",
]
