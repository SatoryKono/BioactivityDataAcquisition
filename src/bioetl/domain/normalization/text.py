"""Pure text normalization helpers."""

from __future__ import annotations

import re
from html import unescape

__all__ = [
    "normalize_string",
    "normalize_to_string",
    "strip_html_tags",
]

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


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
