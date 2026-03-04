"""Date normalization helpers for data normalization service.

Pure functions for partial date normalization and date-parts formatting.
Extracted from DefaultDataNormalizationService to keep class under LOC limit.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


__all__ = [
    "format_date_parts",
    "normalize_partial_date",
]

_DateHandler = Callable[[str], str | None]

_DATE_FULL_FMT = "{0:04d}-{1:02d}-{2:02d}"

# Partial date patterns for end of period normalization
_FULL_DATE_LEN = 10  # YYYY-MM-DD
_PARTIAL_MONTH_LEN = 7  # YYYY-MM
_PARTIAL_YEAR_LEN = 4  # YYYY


def normalize_partial_date(date_str: str | None) -> str | None:
    """Normalize partial date to full YYYY-MM-DD format (end of period).

    Partial dates are normalized to the END of the period:
    - YYYY-MM → YYYY-MM-30 (end of month, day 30 for simplicity)
    - YYYY → YYYY-12-31 (end of year)
    - YYYY-MM-DD → unchanged
    - None/empty → None

    Args:
        date_str: Date string in partial or full ISO format.

    Returns:
        Full ISO date string (YYYY-MM-DD), or None if invalid.
    """
    if not date_str:
        return None
    stripped = date_str.strip()
    if not stripped:
        return None
    return _normalize_by_length(stripped)


def _validate_full_date(date_str: str) -> str | None:
    """Validate YYYY-MM-DD format."""
    return date_str if date_str[4] == "-" and date_str[7] == "-" else None


def _normalize_partial_month(date_str: str) -> str | None:
    """Normalize YYYY-MM to YYYY-MM-30 (end of month)."""
    return f"{date_str}-30" if date_str[4] == "-" else None


def _normalize_partial_year(date_str: str) -> str | None:
    """Normalize YYYY to YYYY-12-31 (end of year)."""
    return f"{date_str}-12-31" if date_str.isdigit() else None


_LENGTH_HANDLERS: dict[int, _DateHandler] = {
    _FULL_DATE_LEN: _validate_full_date,
    _PARTIAL_MONTH_LEN: _normalize_partial_month,
    _PARTIAL_YEAR_LEN: _normalize_partial_year,
}


def _normalize_by_length(date_str: str) -> str | None:
    """Normalize date string based on length pattern."""
    handler = _LENGTH_HANDLERS.get(len(date_str))
    return handler(date_str) if handler else None


def format_date_parts(date_parts: Sequence[Sequence[int]] | None) -> str | None:
    """Format CrossRef date-parts [[year, month?, day?]] to ISO YYYY-MM-DD string.

    Uses end-of-period normalization for partial dates:
    - Complete date [[2024, 3, 15]]: returns "2024-03-15"
    - Month-only [[2024, 3]]: returns "2024-03-31" (last day of month)
    - Year-only [[2024]]: returns "2024-12-31" (last day of year)

    Args:
        date_parts: Date parts.

    Returns:
        The str | None result.
    """
    if not date_parts:
        return None
    parts = date_parts[0]
    if not parts:
        return None
    return _format_parts_to_date(parts)


def _format_parts_to_date(parts: Sequence[int]) -> str:
    """Format date parts to YYYY-MM-DD with end-of-period normalization."""
    from calendar import monthrange

    year = parts[0]
    if len(parts) >= 3:
        return _DATE_FULL_FMT.format(year, parts[1], parts[2])
    if len(parts) == 2:
        return _DATE_FULL_FMT.format(year, parts[1], monthrange(year, parts[1])[1])
    return _DATE_FULL_FMT.format(year, 12, 31)
