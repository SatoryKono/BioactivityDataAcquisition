"""Date normalization helpers for domain-level parsing."""

from __future__ import annotations

from datetime import date

__all__ = [
    "format_date_parts",
    "parse_date_field",
]


_DATE_FULL_FMT = "{0:04d}-{1:02d}-{2:02d}"


def _get_last_day_of_month(year: int, month: int) -> int:
    """Get the last day of the given month."""
    from calendar import monthrange

    return monthrange(year, month)[1]


def _extract_date_parts(date_parts: list[list[int]] | None) -> list[int] | None:
    """Extract first date-parts array if valid, else None."""
    if not date_parts:
        return None
    parts = date_parts[0]
    return parts if parts else None


def _format_parts_to_date(parts: list[int]) -> str:
    """Format date parts to YYYY-MM-DD with end-of-period normalization."""
    year = parts[0]
    if len(parts) >= 3:
        return _DATE_FULL_FMT.format(year, parts[1], parts[2])
    if len(parts) == 2:
        return _DATE_FULL_FMT.format(
            year, parts[1], _get_last_day_of_month(year, parts[1])
        )
    return _DATE_FULL_FMT.format(year, 12, 31)


def format_date_parts(date_parts: list[list[int]] | None) -> str | None:
    """Format CrossRef date-parts [[year, month?, day?]] to ISO YYYY-MM-DD.

    Args:
        date_parts: CrossRef date-parts structure, e.g., [[2023, 5, 15]] or [[2023, 5]].
            Partial dates (year-only, year-month) are normalized to end-of-period.

    Returns:
        ISO 8601 date string (YYYY-MM-DD), or None if input is empty or invalid.
    """
    parts = _extract_date_parts(date_parts)
    if not parts:
        return None
    return _format_parts_to_date(parts)


def parse_date_field(value: str | None, fmt: str = "%Y-%m-%d") -> date | None:
    """Parse date string to date object, return None on error.

    Args:
        value: Date string to parse, or None.
        fmt: strptime format string. Defaults to '%Y-%m-%d'.

    Returns:
        Parsed date object, or None if input is None or does not match format.
    """
    if value is None:
        return None
    from datetime import datetime

    try:
        return datetime.strptime(value.strip(), fmt).date()
    except (ValueError, AttributeError):
        return None
