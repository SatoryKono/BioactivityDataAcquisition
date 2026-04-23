"""Legacy wrapper for page-range normalization helpers.

Deprecated: import from ``bioetl.domain.normalization.pages`` instead.
Sunset target: 2026-06-30.
"""

from __future__ import annotations

from bioetl.domain.normalization.pages import parse_page_range

DEPRECATED_IN_FAVOR_OF = "bioetl.domain.normalization.pages"
SUNSET_DATE = "2026-06-30"

__all__ = ["parse_page_range"]
