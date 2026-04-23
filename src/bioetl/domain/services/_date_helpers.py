"""Legacy wrappers for date normalization helpers.

Deprecated: import pure helpers from ``bioetl.domain.normalization.dates``
instead.
Sunset target: 2026-06-30.
"""

from __future__ import annotations

from bioetl.domain.normalization.dates import format_date_parts, normalize_partial_date

DEPRECATED_IN_FAVOR_OF = "bioetl.domain.normalization.dates"
SUNSET_DATE = "2026-06-30"

__all__ = [
    "format_date_parts",
    "normalize_partial_date",
]
