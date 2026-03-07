"""Pure domain normalization functions (no I/O)."""

from __future__ import annotations

import re
from html import unescape

from bioetl.domain.normalization_authors import (
    extract_first_item,
    extract_first_string,
    parse_authors_to_list,
)
from bioetl.domain.normalization_dates import format_date_parts, parse_date_field
from bioetl.domain.normalization_pages import parse_page_range

__all__ = [
    "extract_first_item",
    "extract_first_string",
    "format_date_parts",
    "normalize_doi",
    "normalize_pmc_id",
    "normalize_string",
    "normalize_to_string",
    "parse_authors_to_list",
    "parse_date_field",
    "parse_page_range",
    "strip_html_tags",
]


def normalize_string(value: str | None) -> str | None:
    """Normalize string by stripping whitespace, return None for empty."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def normalize_to_string(value: object) -> str | None:
    """Convert value to string, strip whitespace, return None if empty."""
    if value is None:
        return None
    str_value = str(value).strip()
    return str_value if str_value else None


def normalize_doi(doi: str | None) -> str | None:
    """Normalize DOI to lowercase, stripped format."""
    return doi.strip().lower() if doi else None


_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def strip_html_tags(text: str | None) -> str | None:
    """Remove HTML/JATS tags, decode entities, normalize whitespace."""
    if not text:
        return None

    clean = text
    if "<" in clean:
        clean = _HTML_TAG_PATTERN.sub("", clean)
    if "&" in clean:
        clean = unescape(clean)
    clean = " ".join(clean.split())
    return clean or None


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
