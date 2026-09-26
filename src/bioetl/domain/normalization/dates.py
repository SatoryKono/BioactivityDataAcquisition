"""Pure date normalization helpers."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date

__all__ = [
    "format_date_parts",
    "normalize_partial_date",
    "parse_date_field",
    "validate_publication_year",
]

_DATE_FULL_FMT = "{0:04d}-{1:02d}-{2:02d}"


def _get_last_day_of_month(year: int, month: int) -> int:
    """Get the last day of the given month."""
    from calendar import monthrange

    return monthrange(year, month)[1]


def _extract_date_parts(
    date_parts: Sequence[Sequence[int]] | None,
) -> Sequence[int] | None:
    """Extract first date-parts array if valid, else None."""
    if not date_parts:
        return None
    parts = date_parts[0]
    return parts if parts else None


def _format_parts_to_date(parts: Sequence[int]) -> str | None:
    """Format date parts to YYYY-MM-DD with end-of-period normalization."""
    if not _date_parts_are_integers(parts):
        return None
    try:
        year = parts[0]
        if len(parts) >= 3:
            normalized = date(year, parts[1], parts[2])
        elif len(parts) == 2:
            month = parts[1]
            normalized = date(year, month, _get_last_day_of_month(year, month))
        else:
            normalized = date(year, 12, 31)
    except (IndexError, TypeError, ValueError):
        return None
    return normalized.isoformat()


def _date_parts_are_integers(parts: Sequence[int]) -> bool:
    """Return whether every consumed date component is a strict integer."""
    return all(type(part) is int for part in parts[:3])


def format_date_parts(date_parts: Sequence[Sequence[int]] | None) -> str | None:
    """Format CrossRef date-parts [[year, month?, day?]] to ISO YYYY-MM-DD."""
    parts = _extract_date_parts(date_parts)
    if not parts:
        return None
    return _format_parts_to_date(parts)


def _validate_full_date(date_str: str) -> str | None:
    """Validate YYYY-MM-DD format using ISO parser."""
    return date_str if _parse_iso8601(date_str) is not None else None


def _normalize_partial_month(date_str: str) -> str | None:
    """Normalize YYYY-MM to end-of-month ISO date."""
    year_month = _parse_year_month(date_str)
    if year_month is None:
        return None
    year, month = year_month
    if month < 1 or month > 12:
        return None
    return _DATE_FULL_FMT.format(year, month, _get_last_day_of_month(year, month))


def _normalize_partial_year(date_str: str) -> str | None:
    """Normalize YYYY to YYYY-12-31."""
    return f"{date_str}-12-31" if date_str.isascii() and date_str.isdecimal() else None


def _parse_year_month(date_str: str) -> tuple[int, int] | None:
    """Parse YYYY-MM date fragments into year/month integers."""
    if len(date_str) != 7 or date_str[4] != "-":
        return None
    try:
        return int(date_str[0:4]), int(date_str[5:7])
    except ValueError:
        return None


def _get_partial_date_normalizer(length: int) -> Callable[[str], str | None] | None:
    """Resolve the canonical normalizer for a stripped partial-date length."""
    return {
        10: _validate_full_date,
        7: _normalize_partial_month,
        4: _normalize_partial_year,
    }.get(length)


def normalize_partial_date(date_str: str | None) -> str | None:
    """Normalize partial or full ISO date to canonical end-of-period ISO date."""
    if not date_str:
        return None
    stripped = date_str.strip()
    if not stripped:
        return None
    normalizer = _get_partial_date_normalizer(len(stripped))
    return None if normalizer is None else normalizer(stripped)


def validate_publication_year(
    year: int | None,
    *,
    min_year: int,
    max_year: int,
) -> tuple[int | None, bool]:
    """Validate publication year against explicit bounds.

    Returns ``(year, is_warning)`` where ``is_warning`` becomes ``True`` when the
    supplied year is outside the configured inclusive range.
    """
    if year is None:
        return None, False
    if min_year <= year <= max_year:
        return year, False
    return year, True


def _parse_iso8601(val_str: str) -> date | None:
    """Fast-path ISO-8601 parser for YYYY-MM-DD strings."""
    if len(val_str) != 10 or val_str[4] != "-" or val_str[7] != "-":
        return None
    try:
        return date(int(val_str[0:4]), int(val_str[5:7]), int(val_str[8:10]))
    except (ValueError, IndexError):
        return None


def parse_date_field(value: str | None, fmt: str = "%Y-%m-%d") -> date | None:
    """Parse date string to date object, return None on error."""
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
