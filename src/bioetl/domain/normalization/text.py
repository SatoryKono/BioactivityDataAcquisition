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
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0e-\x1f\x7f-\x9f]")


def normalize_string(value: str | None) -> str | None:
    """Normalize string by stripping whitespace, return None for empty."""
    if not value:
        return None
    stripped = value.strip()
    return stripped or None


def normalize_to_string(value: object) -> str | None:
    """Convert value to string, strip whitespace, return None if empty."""
    if value is None:
        return None
    str_value = str(value).strip()
    return str_value or None


def strip_html_tags(text: str | None) -> str | None:
    """Remove HTML/JATS tags, decode entities, normalize whitespace."""
    if not text:
        return None

    if "<" in text:
        text = _HTML_TAG_PATTERN.sub("", text)
    if "&" in text:
        text = unescape(text)

    text = " ".join(text.split())
    return text or None


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

    if "<" in text:
        text = _HTML_TAG_PATTERN.sub("", text)
    if "&" in text:
        text = unescape(text)

    text = _CONTROL_CHARS_PATTERN.sub("", text)
    text = unicodedata.normalize("NFC", text)

    text = " ".join(text.split())
    return text or None
