"""Deprecated text normalization compatibility service.

Deprecated: import pure helpers from ``bioetl.domain.normalization.text``
instead.
Sunset target: 2026-06-30.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bioetl.domain.normalization.text import (
    normalize_abstract as _normalize_abstract,
)
from bioetl.domain.normalization.text import (
    normalize_oa_status as _normalize_oa_status,
)
from bioetl.domain.normalization.text import (
    normalize_string as _normalize_string,
)
from bioetl.domain.normalization.text import (
    normalize_title as _normalize_title,
)
from bioetl.domain.normalization.text import (
    normalize_to_string as _normalize_to_string,
)
from bioetl.domain.normalization.text import (
    strip_html_tags as _strip_html_tags,
)

DEPRECATED_IN_FAVOR_OF = "bioetl.domain.normalization.text"
SUNSET_DATE = "2026-06-30"

__all__ = [
    "TextNormalizationService",
]


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
        return _strip_html_tags(text)

    def normalize_oa_status(self, status: str | None) -> str | None:
        """Normalize Open Access status to lowercase.

        Args:
            status: Status value.

        Returns:
            Normalized lowercase status or None.
        """
        return _normalize_oa_status(status)

    def normalize_string(self, value: str | None) -> str | None:
        """Normalize string by stripping whitespace.

        Args:
            value: Input value.

        Returns:
            Stripped string or None if empty.
        """
        return _normalize_string(value)

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
        return _normalize_to_string(value)

    def normalize_title(self, title: str | None) -> str | None:
        """Normalize publication title: HTML cleanup, whitespace, unicode NFC, trim.

        Args:
            title: Raw title string (may contain HTML tags, extra whitespace).

        Returns:
            Normalized title or None if input is None/empty after normalization.
        """
        return _normalize_title(title)

    def normalize_abstract(self, abstract: str | None) -> str | None:
        """Normalize publication abstract: HTML cleanup, whitespace, unicode NFC, trim.

        Args:
            abstract: Raw abstract string (may contain HTML tags, extra whitespace).

        Returns:
            Normalized abstract or None if input is None/empty after normalization.
        """
        return _normalize_abstract(abstract)
