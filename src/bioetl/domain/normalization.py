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


def normalize_to_string(value: Any) -> str | None:  # Any: raw API value for norm...
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
    """Get the last day of the given month."""
    from calendar import monthrange

    return monthrange(year, month)[1]


def _extract_date_parts(date_parts: list[list[int]] | None) -> list[int] | None:
    """Extract first date-parts array if valid, else None."""
    if not date_parts:
        return None
    parts = date_parts[0]
    return parts if parts else None


def format_date_parts(date_parts: list[list[int]] | None) -> str | None:
    """Format CrossRef date-parts [[year, month?, day?]] to ISO YYYY-MM-DD.

    Uses end-of-period normalization: month-only -> last day, year-only -> Dec 31.
    """
    parts = _extract_date_parts(date_parts)
    if not parts:
        return None
    return _format_parts_to_date(parts)


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
    """Remove HTML/JATS tags, decode entities, normalize whitespace."""
    if not text:
        return None

    clean = text

    # Remove HTML tags (only run regex if < is present)
    if "<" in clean:
        clean = _HTML_TAG_PATTERN.sub("", clean)

    # Decode HTML entities (only unescape if & is present)
    if "&" in clean:
        clean = unescape(clean)

    # Fast check for empty/whitespace string
    if not clean or clean.isspace():
        return None

    # Normalize whitespace (split/join is ~3-4x faster than regex)
    clean = " ".join(clean.split())

    return clean if clean else None


# Electronic page identifiers (e-123, E-456, e123) -- not page ranges.
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
    # Rollover: "199-3" -> 203, not 193
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
    """Normalize dashes and split page string on first hyphen.

    Returns (first_page, raw_last_page_or_None). Caller must handle
    empty first_page.
    """
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
    """Parse page range string to (first, last) tuple.

    Handles standard ranges, abbreviated ranges (737-9 -> 739), electronic
    pages (e-123), supplements (S1-S15), and en/em-dash normalization.
    """
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


def normalize_pmc_id(pmc_id: str | None) -> str | None:
    """Normalize PMC ID to uppercase with 'PMC' prefix."""
    if not pmc_id:
        return None
    pmc_id = pmc_id.strip()
    if not pmc_id:
        return None
    if not pmc_id.upper().startswith("PMC"):
        return f"PMC{pmc_id}"
    return pmc_id.upper()


def extract_first_item(items: list[Any] | None) -> Any | None:  # Any: record vals vary
    """Extract first non-None item from list."""
    if not items or not isinstance(items, list):
        return None
    return next((item for item in items if item is not None), None)


def _is_valid_string(item: Any) -> str | None:  # Any: raw API value for normalization
    """Return stripped string if non-empty, else None."""
    return str(item).strip() if item is not None else None


def extract_first_string(items: list[str] | None) -> str | None:
    """Extract first non-empty stripped string from list."""
    if not items or not isinstance(items, list):
        return None
    return next((s for item in items if (s := _is_valid_string(item))), None)


def _filter_valid_strings(items: list[Any]) -> list[str]:  # Any: record vals vary
    """Filter list to valid non-empty strings."""
    return [str(a).strip() for a in items if a is not None and str(a).strip()]


def _parse_authors_from_list(authors: list[Any]) -> list[str]:  # Any: record vals vary
    """Parse author list, filtering non-strings and empty values."""
    return [a.strip() for a in authors if isinstance(a, str) and a.strip()]


def _try_parse_json_array(text: str) -> list[Any] | None:  # Any: record vals vary
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
    """Parse author input (list, JSON string, or delimited string) to list."""
    if authors is None:
        return []
    if isinstance(authors, list):
        return _parse_authors_from_list(authors)
    if isinstance(authors, str) and authors.strip():
        return _parse_authors_string(authors.strip())
    return []
