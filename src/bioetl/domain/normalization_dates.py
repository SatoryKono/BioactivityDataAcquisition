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


def _parse_iso8601(val_str: str) -> date | None:
    """Fast-path ISO-8601 parser for YYYY-MM-DD strings (~6x faster than strptime).

    Args:
        val_str: Stripped date string expected to be in YYYY-MM-DD format.

    Returns:
        Parsed date object, or None if the string is not valid ISO-8601.
    """
    if len(val_str) != 10 or val_str[4] != "-" or val_str[7] != "-":
        return None
    try:
        return date(int(val_str[0:4]), int(val_str[5:7]), int(val_str[8:10]))
    except (ValueError, IndexError):
        return None


def parse_date_field(value: str | None, fmt: str = "%Y-%m-%d") -> date | None:
    """Parse date string to date object, return None on error.

    Args:
        value: Date string to parse, or None.
        fmt: strptime format string. Defaults to '%Y-%m-%d'.

    Returns:
        Parsed date object, or None if input is None or does not match format.

    Notes:
        For ISO-8601 dates (YYYY-MM-DD format), uses fast-path parsing (~6x faster than
        strptime) by direct character position validation and integer conversion. Falls back
        to strptime for other formats or parsing errors.
    """
    if not isinstance(value, str):
        return None

    val_str = value.strip()

    if fmt == "%Y-%m-%d":
        result = _parse_iso8601(val_str)
        if result is not None:
            return result

    from datetime import datetime

    try:
        return datetime.strptime(val_str, fmt).date()
    except ValueError:
        return None
