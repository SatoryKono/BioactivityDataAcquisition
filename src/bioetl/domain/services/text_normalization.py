"""Text normalization service.

Pure domain service (no I/O) per RULES.md §1.1.
Handles HTML stripping, string normalization, and text field cleanup.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from html import unescape
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "TextNormalizationService",
]

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0e-\x1f\x7f-\x9f]")


@dataclass(frozen=True, slots=True)
class TextNormalizationService:
    """Normalize text fields: HTML cleanup, whitespace, unicode NFC.

    Provides methods for general string normalization, HTML stripping,
    and full text field normalization (title, abstract).
    """

    def strip_html_tags(self, text: str | None) -> str | None:
        """Remove HTML tags, decode entities, normalize whitespace.

        Args:
            text: Input text string.

        Returns:
            Cleaned text or None if input is None/empty.
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

    def normalize_oa_status(self, status: str | None) -> str | None:
        """Normalize Open Access status to lowercase.

        Args:
            status: Status value.

        Returns:
            Normalized lowercase status or None.
        """
        if not status:
            return None
        stripped = status.strip()
        return stripped.lower() if stripped else None

    def normalize_string(self, value: str | None) -> str | None:
        """Normalize string by stripping whitespace.

        Args:
            value: Input value.

        Returns:
            Stripped string or None if empty.
        """
        if value is None:
            return None
        stripped = value.strip()
        return stripped if stripped else None

    def normalize_to_string(
        self,
        value: Any,  # Any: raw input value from API (str|int|float|None)
    ) -> str | None:  # Any: raw input value from API (str|int|float|None)
        """Convert value to string, strip whitespace, return None if empty.

        Args:
            value: Input value.

        Returns:
            String representation or None.
        """
        if value is None:
            return None
        str_value = str(value).strip()
        return str_value if str_value else None

    def normalize_title(self, title: str | None) -> str | None:
        """Normalize publication title: HTML cleanup, whitespace, unicode NFC, trim.

        Args:
            title: Raw title string (may contain HTML tags, extra whitespace).

        Returns:
            Normalized title or None if input is None/empty after normalization.
        """
        return self._normalize_text_field(title)

    def normalize_abstract(self, abstract: str | None) -> str | None:
        """Normalize publication abstract: HTML cleanup, whitespace, unicode NFC, trim.

        Args:
            abstract: Raw abstract string (may contain HTML tags, extra whitespace).

        Returns:
            Normalized abstract or None if input is None/empty after normalization.
        """
        return self._normalize_text_field(abstract)

    def _normalize_text_field(self, text: str | None) -> str | None:
        """Normalize text field through complete pipeline.

        Pipeline: HTML strip -> control chars -> NFC unicode -> collapse whitespace -> trim.
        """
        if not text:
            return None

        normalized = text
        for step in self._text_normalization_steps():
            normalized = step(normalized)

        normalized = normalized.strip()
        return normalized if normalized else None

    def _text_normalization_steps(self) -> tuple[Callable[[str], str], ...]:
        """Return normalization strategy chain for text fields."""
        return (
            _strip_html_and_decode_entities,
            _remove_control_characters,
            _normalize_unicode_nfc,
            _collapse_whitespace,
        )


def _strip_html_and_decode_entities(text: str) -> str:
    """Strip HTML tags and decode HTML entities."""
    # Optimization: Conditionally bypass regex and unescape if characters are absent
    if "<" in text:
        text = _HTML_TAG_PATTERN.sub("", text)
    if "&" in text:
        text = unescape(text)
    return text


def _remove_control_characters(text: str) -> str:
    """Remove non-whitespace control characters."""
    return _CONTROL_CHARS_PATTERN.sub("", text)


def _normalize_unicode_nfc(text: str) -> str:
    """Normalize unicode using NFC canonical composition."""
    return unicodedata.normalize("NFC", text)


def _collapse_whitespace(text: str) -> str:
    """Collapse any whitespace sequence into a single space."""
    # Optimization: str.split/join is faster than regex for whitespace collapse
    return " ".join(text.split())
