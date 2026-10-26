"""Pure text normalization helpers."""

from __future__ import annotations

import re
import unicodedata
from html import unescape

__all__ = [
    "normalize_abstract",
    "normalize_oa_status",
    "normalize_string",
    "normalize_title",
    "normalize_to_string",
    "strip_html_tags",
]

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0e-\x1f\x7f-\x9f]")


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


def normalize_oa_status(status: str | None) -> str | None:
    """Normalize Open Access status to lowercase."""
    normalized = normalize_string(status)
    return normalized.lower() if normalized is not None else None


def normalize_title(title: str | None) -> str | None:
    """Normalize publication title with deterministic text cleanup."""
    return _normalize_text_field(title)


def normalize_abstract(abstract: str | None) -> str | None:
    """Normalize publication abstract with deterministic text cleanup."""
    return _normalize_text_field(abstract)


def _normalize_text_field(text: str | None) -> str | None:
    """Normalize text field through complete cleanup pipeline."""
    if not text:
        return None

    normalized = text
    for step in (
        _strip_html_and_decode_entities,
        _remove_control_characters,
        _normalize_unicode_nfc,
        _collapse_whitespace,
    ):
        normalized = step(normalized)

    normalized = normalized.strip()
    return normalized if normalized else None


def _strip_html_and_decode_entities(text: str) -> str:
    """Strip HTML tags and decode HTML entities."""
    return unescape(_HTML_TAG_PATTERN.sub("", text))


def _remove_control_characters(text: str) -> str:
    """Remove non-whitespace control characters."""
    return _CONTROL_CHARS_PATTERN.sub("", text)


def _normalize_unicode_nfc(text: str) -> str:
    """Normalize unicode using NFC canonical composition."""
    return unicodedata.normalize("NFC", text)


def _collapse_whitespace(text: str) -> str:
    """Collapse any whitespace sequence into a single space."""
    return _WHITESPACE_PATTERN.sub(" ", text)
