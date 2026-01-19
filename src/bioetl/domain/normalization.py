"""Pure domain normalization functions (no I/O).

REFACTOR-004: Domain logic separation from use-case layer.
"""

from __future__ import annotations

import re
from datetime import date
from html import unescape
from typing import Any

from bioetl.domain.serialization import deserialize_from_json


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
_DATE_FULL_FMT = "{0:04d}-{1:02d}-{2:02d}"


def _get_last_day_of_month(year: int, month: int) -> int:
    """Get the last day of the given month.

    Args:
        year: Year (used for leap year calculation in February).
        month: Month (1-12).

    Returns:
        Last day of the month (28-31).
    """
    from calendar import monthrange

    return monthrange(year, month)[1]


def format_date_parts(date_parts: list[list[int]] | None) -> str | None:
    """Format CrossRef date-parts [[year, month?, day?]] to ISO YYYY-MM-DD string.

    Uses end-of-period normalization for partial dates:
    - Complete date [[2024, 3, 15]]: returns "2024-03-15"
    - Month-only [[2024, 3]]: returns "2024-03-31" (last day of month)
    - Year-only [[2024]]: returns "2024-12-31" (last day of year)

    Args:
        date_parts: CrossRef date-parts array [[year, month?, day?]].

    Returns:
        ISO date string (YYYY-MM-DD) or None if input is invalid.
    """
    if not date_parts or not date_parts[0]:
        return None
    parts = date_parts[0]
    num_parts = len(parts)

    if num_parts == 0:
        return None

    year = parts[0]

    if num_parts >= 3:
        # Complete date: YYYY-MM-DD
        return _DATE_FULL_FMT.format(year, parts[1], parts[2])
    elif num_parts == 2:
        # Month-only: use last day of month
        month = parts[1]
        last_day = _get_last_day_of_month(year, month)
        return _DATE_FULL_FMT.format(year, month, last_day)
    else:
        # Year-only: use December 31st
        return _DATE_FULL_FMT.format(year, 12, 31)


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
_WHITESPACE_PATTERN = re.compile(r"\s+")


def strip_html_tags(text: str | None) -> str | None:
    """Remove HTML tags and decode entities from text.

    Performs the following normalization steps:
    1. Remove HTML tags (including JATS tags like <jats:p>)
    2. Decode HTML entities (&amp; → &, &lt; → <, etc.)
    3. Normalize whitespace (collapse multiple spaces to single space)
    4. Strip leading/trailing whitespace

    Args:
        text: Input text possibly containing HTML.

    Returns:
        Clean text without HTML tags, or None if input is None/empty.

    """
    if not text:
        return None

    # Remove HTML tags
    clean = _HTML_TAG_PATTERN.sub("", text)

    # Decode HTML entities (&amp; → &, &lt; → <, etc.)
    clean = unescape(clean)

    # Normalize whitespace (collapse multiple spaces/newlines to single space)
    clean = _WHITESPACE_PATTERN.sub(" ", clean).strip()

    return clean if clean else None


def _to_none_if_empty(s: str) -> str | None:
    """Return None if string is empty after strip."""
    return s.strip() or None


def parse_page_range(page: str | None) -> tuple[str | None, str | None]:
    """Parse page range '123-456' to (first, last) tuple."""
    if not page:
        return None, None
    first, sep, last = page.partition("-")
    return _to_none_if_empty(first), _to_none_if_empty(last) if sep else None


def normalize_pmc_id(pmc_id: str | None) -> str | None:
    """Normalize PMC ID to uppercase with 'PMC' prefix.

    Ensures PMC IDs are consistently formatted across providers
    for cross-referencing publications.

    Args:
        pmc_id: Raw PMC ID (may or may not have 'PMC' prefix).

    Returns:
        Normalized PMC ID with 'PMC' prefix in uppercase,
        or None if input is empty.

    Examples:
        >>> normalize_pmc_id("PMC1234567")
        'PMC1234567'
        >>> normalize_pmc_id("1234567")
        'PMC1234567'
        >>> normalize_pmc_id("pmc1234567")
        'PMC1234567'
        >>> normalize_pmc_id(None)

    """
    if not pmc_id:
        return None
    pmc_id = pmc_id.strip()
    if not pmc_id:
        return None
    if not pmc_id.upper().startswith("PMC"):
        return f"PMC{pmc_id}"
    return pmc_id.upper()


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


def _filter_valid_strings(items: list[Any]) -> list[str]:
    """Filter list to valid non-empty strings."""
    return [str(a).strip() for a in items if a is not None and str(a).strip()]


def _parse_authors_from_list(authors: list[Any]) -> list[str]:
    """Parse author list, filtering non-strings and empty values."""
    return [a.strip() for a in authors if isinstance(a, str) and a.strip()]


def _try_parse_json_array(text: str) -> list[Any] | None:
    """Try to parse text as JSON array. Returns None if invalid."""
    try:
        parsed = deserialize_from_json(text)
        return parsed if isinstance(parsed, list) else None
    except ValueError:
        return None


def _parse_authors_from_json(text: str) -> list[str] | None:
    """Try to parse JSON array of authors. Returns None if not valid JSON."""
    if not text.startswith("["):
        return None
    parsed = _try_parse_json_array(text)
    return _filter_valid_strings(parsed) if parsed is not None else None


def _parse_authors_from_delimited(text: str) -> list[str]:
    """Parse delimited string (semicolon or comma separated)."""
    delimiter = ";" if ";" in text else ","
    parts = text.split(delimiter) if delimiter in text else [text]
    return [a.strip() for a in parts if a.strip()]


def _parse_authors_string(text: str) -> list[str]:
    """Parse string as JSON or delimited format."""
    json_result = _parse_authors_from_json(text)
    return (
        json_result if json_result is not None else _parse_authors_from_delimited(text)
    )


def parse_authors_to_list(authors: list[str] | str | None) -> list[str]:
    """Parse various author input formats into a list of author names.

    Supports:
    - list[str]: Direct list of authors (returned as-is with stripping)
    - str (JSON): JSON-serialized list (e.g., '["John Doe", "Jane Smith"]')
    - str (concatenated): Semicolon or comma-separated string
      (e.g., "John Doe; Jane Smith" or "John Doe, Jane Smith")

    Args:
        authors: Raw author data in various formats.

    Returns:
        List of individual author names (empty list if None or empty).
        Each name is stripped of whitespace.

    Example:
        >>> parse_authors_to_list(["John Doe", "Jane Smith"])
        ['John Doe', 'Jane Smith']
        >>> parse_authors_to_list('["John Doe", "Jane Smith"]')
        ['John Doe', 'Jane Smith']
        >>> parse_authors_to_list("John Doe; Jane Smith")
        ['John Doe', 'Jane Smith']
        >>> parse_authors_to_list("John Doe, Jane Smith")
        ['John Doe', 'Jane Smith']
        >>> parse_authors_to_list(None)
        []
    """
    if authors is None:
        return []
    if isinstance(authors, list):
        return _parse_authors_from_list(authors)
    if isinstance(authors, str) and authors.strip():
        return _parse_authors_string(authors.strip())
    return []
