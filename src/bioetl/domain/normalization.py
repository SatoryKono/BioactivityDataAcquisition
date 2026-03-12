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
    "strip_doi_prefix",
    "strip_html_tags",
]


def normalize_string(value: str | None) -> str | None:
    """Normalize string by stripping whitespace, return None for empty.

    Args:
        value: Input string or None.

    Returns:
        Stripped string, or None if input is None or whitespace-only.
    """
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def normalize_to_string(value: object) -> str | None:
    """Convert value to string, strip whitespace, return None if empty.

    Args:
        value: Any value to coerce to string. None returns None.

    Returns:
        Stripped string representation, or None if result is empty.
    """
    if value is None:
        return None
    str_value = str(value).strip()
    return str_value if str_value else None


_DOI_URL_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "doi:",
    "DOI:",
)


def strip_doi_prefix(doi: str) -> str:
    """Strip known DOI URL/scheme prefixes, preserving the DOI payload.

    Handles: ``https://doi.org/``, ``http://doi.org/``, ``doi:``, ``DOI:``.
    Does NOT lowercase or strip whitespace — caller decides post-processing.

    Args:
        doi: Raw DOI string that may contain URL-style or scheme prefixes.

    Returns:
        DOI string with supported prefixes removed.
    """
    for prefix in _DOI_URL_PREFIXES:
        if doi.startswith(prefix):
            return doi[len(prefix):]
    return doi


def normalize_doi(doi: str | None) -> str | None:
    """Normalize DOI to lowercase, stripped format.

    Args:
        doi: Raw DOI string or None.

    Returns:
        Lowercase, stripped DOI string, or None if input is falsy.
    """
    return doi.strip().lower() if doi else None


_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def strip_html_tags(text: str | None) -> str | None:
    """Remove HTML/JATS tags, decode entities, normalize whitespace.

    Args:
        text: Raw text possibly containing HTML or JATS markup.

    Returns:
        Clean text with tags stripped, entities decoded, and whitespace collapsed.
        Returns None if input is falsy or result is empty.
    """
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
    """Normalize PMC ID to uppercase with 'PMC' prefix.

    Args:
        pmc_id: Raw PMC ID string, with or without the 'PMC' prefix.

    Returns:
        Uppercase PMC ID with 'PMC' prefix (e.g., 'PMC123456'), or None if empty.
    """
    if not pmc_id:
        return None
    pmc_id = pmc_id.strip()
    if not pmc_id:
        return None
    if not pmc_id.upper().startswith("PMC"):
        return f"PMC{pmc_id}"
    return pmc_id.upper()
