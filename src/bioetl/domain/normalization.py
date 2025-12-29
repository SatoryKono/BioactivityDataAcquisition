"""Pure domain normalization functions (no I/O).

REFACTOR-004: Domain logic separation from use-case layer.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any


def normalize_string(value: str | None) -> str | None:
    """Normalize string by stripping whitespace, return None for empty."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def normalize_to_string(value: Any) -> str | None:
    """Convert value to string, strip whitespace, return None if empty."""
    if value is None:
        return None
    str_value = str(value).strip()
    return str_value if str_value else None


def normalize_doi(doi: str | None) -> str | None:
    """Normalize DOI to lowercase, stripped format."""
    return doi.strip().lower() if doi else None


# Date formatting helpers
_DATE_FORMATS = {3: "{0:04d}-{1:02d}-{2:02d}", 2: "{0:04d}-{1:02d}", 1: "{0:04d}"}


def format_date_parts(date_parts: list[list[int]] | None) -> str | None:
    """Format CrossRef date-parts [[year, month?, day?]] to ISO string."""
    if not date_parts or not date_parts[0]:
        return None
    parts = date_parts[0]
    fmt = _DATE_FORMATS.get(min(len(parts), 3))
    return fmt.format(*parts) if fmt else None


def parse_date_field(value: str | None, fmt: str = "%Y-%m-%d") -> date | None:
    """Parse date string to date object, return None on error."""
    if value is None:
        return None
    from datetime import datetime
    try:
        return datetime.strptime(value.strip(), fmt).date()
    except (ValueError, AttributeError):
        return None


_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def strip_html_tags(text: str | None) -> str | None:
    """Strip HTML tags from text, return None if empty."""
    if not text:
        return None
    result = _HTML_TAG_PATTERN.sub("", text).strip()
    return result if result else None


def _to_none_if_empty(s: str) -> str | None:
    """Return None if string is empty after strip."""
    return s.strip() or None


def parse_page_range(page: str | None) -> tuple[str | None, str | None]:
    """Parse page range '123-456' to (first, last) tuple."""
    if not page:
        return None, None
    first, sep, last = page.partition("-")
    return _to_none_if_empty(first), _to_none_if_empty(last) if sep else None


def extract_first_item(items: list[Any] | None) -> Any | None:
    """Extract first non-None item from list."""
    if not items or not isinstance(items, list):
        return None
    return next((item for item in items if item is not None), None)


def _is_valid_string(item: Any) -> str | None:
    """Return stripped string if non-empty, else None."""
    return str(item).strip() if item is not None else None


def extract_first_string(items: list[str] | None) -> str | None:
    """Extract first non-empty stripped string from list."""
    if not items or not isinstance(items, list):
        return None
    return next((s for item in items if (s := _is_valid_string(item))), None)
