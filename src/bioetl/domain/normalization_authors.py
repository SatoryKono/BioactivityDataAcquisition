"""Legacy wrapper for author-list parsing helpers.

Deprecated: import from ``bioetl.domain.normalization.authors`` instead.
Sunset target: 2026-06-30.
"""

from __future__ import annotations

from bioetl.domain.normalization.authors import (
    extract_first_item,
    extract_first_string,
    parse_authors_to_list,
)

DEPRECATED_IN_FAVOR_OF = "bioetl.domain.normalization.authors"
SUNSET_DATE = "2026-06-30"

__all__ = [
    "extract_first_item",
    "extract_first_string",
    "parse_authors_to_list",
]
