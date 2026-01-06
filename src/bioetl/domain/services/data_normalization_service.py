"""Data normalization service for text and publication metadata.

Provides a unified interface for normalizing publication metadata,
identifiers, and text content from various data sources.

This service consolidates normalization functions that were previously
scattered across domain/normalization.py, domain/validation.py,
and application/core/field_specs.py.

Pure domain service (no I/O) per RULES.md §1.1.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from html import unescape
from typing import TYPE_CHECKING, Any

from bioetl.domain.services.data_normalization_config import DataNormalizationConfig

if TYPE_CHECKING:
    from collections.abc import Sequence


# =============================================================================
# Pre-compiled regex patterns for performance
# =============================================================================

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")

# Date formatting helpers
_DATE_FORMATS = {
    3: "{0:04d}-{1:02d}-{2:02d}",
    2: "{0:04d}-{1:02d}",
    1: "{0:04d}",
}


@dataclass(slots=True)
class DefaultDataNormalizationService:
    """Default implementation of data normalization service.

    Orchestrates text and data normalization for publication metadata,
    identifiers, and text content.

    This service is a thin wrapper following the Facade pattern.
    All business logic is implemented as pure functions.

    Attributes:
        config: Configuration for normalization behavior.

    Example:
        >>> config = DataNormalizationConfig()
        >>> service = DefaultDataNormalizationService(config)
        >>> service.normalize_doi("10.1038/NATURE12373")
        '10.1038/nature12373'
        >>> service.normalize_year(2024)
        (2024, False)
    """

    config: DataNormalizationConfig = field(default_factory=DataNormalizationConfig)

    # ========================================================================
    # Identifier Normalization
    # ========================================================================

    def normalize_doi(self, doi: str | None) -> str | None:
        """Normalize DOI identifier to lowercase, stripped format.

        Args:
            doi: DOI string to normalize.

        Returns:
            Normalized DOI (lowercase, stripped) or None if input is None/empty.

        Example:
            >>> service.normalize_doi("10.1038/NATURE12373")
            '10.1038/nature12373'
        """
        return doi.strip().lower() if doi else None

    def normalize_pmid(self, pmid: str | int | None) -> str | None:
        """Normalize PubMed ID to string format.

        Converts int or string PMID to normalized string representation.
        Returns None for invalid inputs.

        Args:
            pmid: Raw PMID value (int, str, or None).

        Returns:
            Normalized PMID string (digits only), or None if invalid.

        Example:
            >>> service.normalize_pmid(12345678)
            '12345678'
            >>> service.normalize_pmid("  12345678  ")
            '12345678'
        """
        str_value = self._pmid_to_string(pmid)
        if str_value is None:
            return None
        return self._validate_pmid_string(str_value)

    def _pmid_to_string(self, pmid: str | int | None) -> str | None:
        """Convert PMID to string, rejecting invalid types."""
        if pmid is None or isinstance(pmid, bool):
            return None
        if isinstance(pmid, (int, str)):
            result = str(pmid).strip()
            return result if result else None
        return None

    def _validate_pmid_string(self, str_value: str) -> str | None:
        """Validate and normalize PMID string."""
        if not str_value.isdigit():
            return None
        int_value = int(str_value)
        return str(int_value) if int_value > 0 else None

    # ========================================================================
    # Year Normalization
    # ========================================================================

    def normalize_year(self, year: int | None) -> tuple[int | None, bool]:
        """Validate and normalize publication year.

        Uses configured publication year range.
        Values outside this range are preserved but flagged for DQ warnings.

        Args:
            year: Publication year to validate.

        Returns:
            Tuple of (year, is_warning) where:
            - year: Original value (preserved even if out of range)
            - is_warning: True if year is outside valid range (requires DQ warning)

        Example:
            >>> service.normalize_year(2024)
            (2024, False)
            >>> service.normalize_year(1799)
            (1799, True)
        """
        if year is None:
            return None, False
        if self.config.min_publication_year <= year <= self.config.max_publication_year:
            return year, False
        return year, True  # Keep value but flag as warning

    # ========================================================================
    # Author Normalization
    # ========================================================================

    def normalize_authors(
        self,
        authors: list[str] | str | None,
        salt: str,
    ) -> str | None:
        """Normalize and hash author names for PII protection.

        Parses various author input formats, hashes each author name
        with the provided salt, and serializes to JSON string.

        Args:
            authors: Raw author data in various formats.
            salt: Salt string for hashing author names (PII protection).

        Returns:
            JSON-serialized list of hashed author names, or None if empty.

        Example:
            >>> service.normalize_authors(["John Doe"], salt="secret")
            '["e5d9...]'
        """
        # Parse to list
        author_list = self.parse_authors_to_list(authors)
        if not author_list:
            return None

        # Hash each author
        hashed_authors = [self._hash_pii(name, salt) for name in author_list]

        # Serialize to JSON
        return json.dumps(hashed_authors, ensure_ascii=True)

    def _hash_pii(self, value: str, salt: str) -> str:
        """Hash a PII value with salt using SHA-256.

        Args:
            value: Value to hash.
            salt: Salt for hashing.

        Returns:
            SHA-256 hash of salted value.
        """
        salted = f"{salt}{value}"
        return hashlib.sha256(salted.encode("utf-8")).hexdigest()

    # ========================================================================
    # Text Normalization
    # ========================================================================

    def strip_html_tags(self, text: str | None) -> str | None:
        """Remove HTML tags and decode entities from text.

        Performs the following normalization steps:
        1. Remove HTML tags (including JATS tags like <jats:p>)
        2. Decode HTML entities (&amp; -> &, &lt; -> <, etc.)
        3. Normalize whitespace (collapse multiple spaces to single space)
        4. Strip leading/trailing whitespace

        Args:
            text: Input text possibly containing HTML.

        Returns:
            Clean text without HTML tags, or None if input is None/empty.

        Example:
            >>> service.strip_html_tags("<p>Hello &amp; world</p>")
            'Hello & world'
        """
        if not text:
            return None

        # Remove HTML tags
        clean = _HTML_TAG_PATTERN.sub("", text)

        # Decode HTML entities (&amp; -> &, &lt; -> <, etc.)
        clean = unescape(clean)

        # Normalize whitespace (collapse multiple spaces/newlines to single space)
        clean = _WHITESPACE_PATTERN.sub(" ", clean).strip()

        return clean if clean else None

    def normalize_oa_status(self, status: str | None) -> str | None:
        """Normalize Open Access status to lowercase.

        Standardizes OA status values (gold, green, bronze, hybrid, closed)
        to lowercase for consistent comparison.

        Args:
            status: Open Access status string.

        Returns:
            Lowercase status string, or None if input is None/empty.

        Example:
            >>> service.normalize_oa_status("GOLD")
            'gold'
        """
        if not status:
            return None
        stripped = status.strip()
        return stripped.lower() if stripped else None

    def normalize_string(self, value: str | None) -> str | None:
        """Normalize string by stripping whitespace.

        Args:
            value: String to normalize.

        Returns:
            Stripped string, or None if input is None/empty.

        Example:
            >>> service.normalize_string("  hello  ")
            'hello'
        """
        if value is None:
            return None
        stripped = value.strip()
        return stripped if stripped else None

    # ========================================================================
    # Author Parsing
    # ========================================================================

    def parse_authors_to_list(
        self,
        authors: list[str] | str | None,
    ) -> list[str]:
        """Parse various author input formats into a list of author names.

        Supports:
        - list[str]: Direct list of authors (returned as-is with stripping)
        - str (JSON): JSON-serialized list
        - str (concatenated): Semicolon or comma-separated string

        Args:
            authors: Raw author data in various formats.

        Returns:
            List of individual author names (empty list if None or empty).

        Example:
            >>> service.parse_authors_to_list(["John Doe", "Jane Smith"])
            ['John Doe', 'Jane Smith']
            >>> service.parse_authors_to_list("John Doe; Jane Smith")
            ['John Doe', 'Jane Smith']
        """
        if authors is None:
            return []
        if isinstance(authors, list):
            return self._parse_authors_from_list(authors)
        if isinstance(authors, str) and authors.strip():
            return self._parse_authors_string(authors.strip())
        return []

    def _parse_authors_from_list(self, authors: list[Any]) -> list[str]:
        """Parse author list, filtering non-strings and empty values."""
        return [a.strip() for a in authors if isinstance(a, str) and a.strip()]

    def _parse_authors_string(self, text: str) -> list[str]:
        """Parse string as JSON or delimited format."""
        json_result = self._parse_authors_from_json(text)
        return (
            json_result
            if json_result is not None
            else self._parse_authors_from_delimited(text)
        )

    def _parse_authors_from_json(self, text: str) -> list[str] | None:
        """Try to parse JSON array of authors. Returns None if not valid JSON."""
        if not text.startswith("["):
            return None
        parsed = self._try_parse_json_array(text)
        return self._filter_valid_strings(parsed) if parsed is not None else None

    def _try_parse_json_array(self, text: str) -> list[Any] | None:
        """Try to parse text as JSON array. Returns None if invalid."""
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else None
        except json.JSONDecodeError:
            return None

    def _filter_valid_strings(self, items: list[Any]) -> list[str]:
        """Filter list to valid non-empty strings."""
        return [str(a).strip() for a in items if a is not None and str(a).strip()]

    def _parse_authors_from_delimited(self, text: str) -> list[str]:
        """Parse delimited string (semicolon or comma separated)."""
        delimiter = ";" if ";" in text else ","
        parts = text.split(delimiter) if delimiter in text else [text]
        return [a.strip() for a in parts if a.strip()]

    # ========================================================================
    # Date Formatting
    # ========================================================================

    def format_date_parts(
        self,
        date_parts: Sequence[Sequence[int]] | None,
    ) -> str | None:
        """Format CrossRef date-parts [[year, month?, day?]] to ISO string.

        Args:
            date_parts: Date parts in CrossRef format.

        Returns:
            ISO date string (YYYY-MM-DD, YYYY-MM, or YYYY), or None.

        Example:
            >>> service.format_date_parts([[2024, 3, 15]])
            '2024-03-15'
            >>> service.format_date_parts([[2024, 3]])
            '2024-03'
        """
        if not date_parts or not date_parts[0]:
            return None
        parts = date_parts[0]
        fmt = _DATE_FORMATS.get(min(len(parts), 3))
        return fmt.format(*parts) if fmt else None
