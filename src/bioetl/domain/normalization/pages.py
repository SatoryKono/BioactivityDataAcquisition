"""Page-range normalization helpers."""

from __future__ import annotations

import re

__all__ = ["parse_page_range"]

_ELECTRONIC_PAGE_PATTERN = re.compile(r"^[eE]-?\d+$")


def _is_electronic_page(page: str) -> bool:
    """Check if page is electronic article number (e.g., 'e-123', 'e123')."""
    return bool(_ELECTRONIC_PAGE_PATTERN.match(page))


def _extract_digits(s: str) -> str:
    """Extract only digit characters from a string."""
    return "".join(c for c in s if c.isdigit())


def _extract_non_digits(s: str) -> str:
    """Extract only non-digit characters from a string."""
    return "".join(c for c in s if not c.isdigit())


def _is_abbreviated(first_digits: str, last_digits: str) -> bool:
    """Return True if last_digits is an abbreviated form of first_digits."""
    return (
        bool(first_digits)
        and bool(last_digits)
        and len(last_digits) < len(first_digits)
    )


def _compute_expanded_page(first_digits: str, last_digits: str) -> int:
    """Compute expanded page number with rollover handling."""
    first_num = int(first_digits)
    divisor = 10 ** len(last_digits)
    expanded = (first_num // divisor) * divisor + int(last_digits)
    return int(expanded + divisor) if expanded < first_num else int(expanded)


def _expand_abbreviated_page(first_page: str, last_page_raw: str) -> str:
    """Expand abbreviated last page (e.g., 737-9 -> 739, 199-3 -> 203)."""
    first_digits = _extract_digits(first_page)
    last_digits = _extract_digits(last_page_raw)
    if not _is_abbreviated(first_digits, last_digits):
        return last_page_raw

    expanded = _compute_expanded_page(first_digits, last_digits)
    prefix = _extract_non_digits(last_page_raw)
    return f"{prefix}{expanded}" if prefix else str(expanded)


def _normalize_and_split_pages(page: str) -> tuple[str, str | None]:
    """Normalize dashes and split page string on first hyphen."""
    normalized = page.replace("\u2013", "-").replace("\u2014", "-")
    parts = normalized.split("-", 1)
    first = parts[0].strip()
    last = parts[1].strip() if len(parts) > 1 else None
    return first, last or None


def _prepare_page_input(page: str | None) -> str | None:
    """Strip and return page string, or None if empty."""
    if not page:
        return None
    stripped = page.strip()
    return stripped if stripped else None


def parse_page_range(page: str | None) -> tuple[str | None, str | None]:
    """Parse page range string to (first, last) tuple."""
    stripped = _prepare_page_input(page)
    if stripped is None:
        return None, None
    if _is_electronic_page(stripped):
        return stripped, None

    first_page, last_page_raw = _normalize_and_split_pages(stripped)
    if not first_page:
        return None, None

    last_page = (
        _expand_abbreviated_page(first_page, last_page_raw) if last_page_raw else None
    )
    return first_page, last_page
