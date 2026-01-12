"""Data normalization port interfaces (Protocols).

Defines contracts for text and data normalization operations:
- DOI normalization
- PMID normalization
- Year validation
- Author name normalization
- HTML tag stripping
- Open Access status normalization

This port is distinct from NormalizationServicePort which handles
bioactivity value normalization (unit conversion, pChEMBL, etc.).

All ports follow the Ports & Adapters pattern per RULES.md §1.1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence


@runtime_checkable
class DataNormalizationPort(Protocol):
    """Port for text and data normalization operations.

    Provides a unified interface for normalizing publication metadata,
    identifiers, and text content from various data sources.

    This service consolidates normalization functions that were previously
    scattered across domain/normalization.py, domain/validation.py,
    and application/core/field_specs.py.

    Example:
        >>> from bioetl.domain.services import DataNormalizationService
        >>> normalizer = DataNormalizationService()
        >>> normalizer.normalize_doi("10.1038/NATURE12373")
        '10.1038/nature12373'
        >>> normalizer.normalize_pmid(12345678)
        '12345678'
        >>> normalizer.normalize_year(2024)
        (2024, False)
    """

    def normalize_doi(self, doi: str | None) -> str | None:
        """Normalize DOI identifier to lowercase, stripped format.

        Handles DOIs in various formats:
        - Bare DOI: "10.1038/nature12373"
        - HTTPS URL: "https://doi.org/10.1038/nature12373"
        - HTTP URL: "http://doi.org/10.1038/nature12373"
        - doi: prefix: "doi:10.1038/nature12373"

        Args:
            doi: DOI string in any supported format.

        Returns:
            Normalized bare DOI (lowercase, stripped) or None if input is None/empty.

        Example:
            >>> normalize_doi("10.1038/NATURE12373")
            '10.1038/nature12373'
            >>> normalize_doi("https://doi.org/10.1038/nature12373")
            '10.1038/nature12373'
            >>> normalize_doi("  10.1038/nature12373  ")
            '10.1038/nature12373'
            >>> normalize_doi(None)
            None
        """
        ...

    def normalize_pmid(self, pmid: str | int | None) -> str | None:
        """Normalize PubMed ID to string format.

        Converts int or string PMID to normalized string representation.
        Returns None for invalid inputs.

        Args:
            pmid: Raw PMID value (int, str, or None).

        Returns:
            Normalized PMID string (digits only), or None if invalid.

        Example:
            >>> normalize_pmid(12345678)
            '12345678'
            >>> normalize_pmid("  12345678  ")
            '12345678'
            >>> normalize_pmid("abc")
            None
            >>> normalize_pmid(None)
            None
        """
        ...

    def normalize_year(self, year: int | None) -> tuple[int | None, bool]:
        """Validate and normalize publication year.

        Uses standard publication year range [1800, 2100].
        Values outside this range are preserved but flagged for DQ warnings.

        Args:
            year: Publication year to validate.

        Returns:
            Tuple of (year, is_warning) where:
            - year: Original value (preserved even if out of range)
            - is_warning: True if year is outside valid range (requires DQ warning)

        Example:
            >>> normalize_year(2024)
            (2024, False)
            >>> normalize_year(1799)
            (1799, True)
            >>> normalize_year(None)
            (None, False)
        """
        ...

    def normalize_authors(
        self,
        authors: list[str] | str | None,
        salt: str,
    ) -> str | None:
        """Normalize and hash author names for PII protection.

        Parses various author input formats, hashes each author name
        with the provided salt, and serializes to JSON string.

        Args:
            authors: Raw author data in various formats:
                - list[str]: Direct list of authors
                - str (JSON): JSON-serialized list
                - str (concatenated): Semicolon or comma-separated string
            salt: Salt string for hashing author names (PII protection).

        Returns:
            JSON-serialized list of hashed author names, or None if empty.

        Example:
            >>> normalize_authors(["John Doe", "Jane Smith"], salt="secret")
            '["hash1", "hash2"]'
            >>> normalize_authors("John Doe; Jane Smith", salt="secret")
            '["hash1", "hash2"]'
            >>> normalize_authors(None, salt="secret")
            None
        """
        ...

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
            >>> strip_html_tags("<p>Hello &amp; world</p>")
            'Hello & world'
            >>> strip_html_tags("<jats:p>Abstract text</jats:p>")
            'Abstract text'
            >>> strip_html_tags(None)
            None
        """
        ...

    def normalize_oa_status(self, status: str | None) -> str | None:
        """Normalize Open Access status to lowercase.

        Standardizes OA status values (gold, green, bronze, hybrid, closed)
        to lowercase for consistent comparison.

        Args:
            status: Open Access status string.

        Returns:
            Lowercase status string, or None if input is None/empty.

        Example:
            >>> normalize_oa_status("GOLD")
            'gold'
            >>> normalize_oa_status("Green")
            'green'
            >>> normalize_oa_status(None)
            None
        """
        ...

    def normalize_string(self, value: str | None) -> str | None:
        """Normalize string by stripping whitespace.

        Args:
            value: String to normalize.

        Returns:
            Stripped string, or None if input is None/empty.

        Example:
            >>> normalize_string("  hello  ")
            'hello'
            >>> normalize_string("   ")
            None
        """
        ...

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
            >>> parse_authors_to_list(["John Doe", "Jane Smith"])
            ['John Doe', 'Jane Smith']
            >>> parse_authors_to_list("John Doe; Jane Smith")
            ['John Doe', 'Jane Smith']
            >>> parse_authors_to_list(None)
            []
        """
        ...

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
            >>> format_date_parts([[2024, 3, 15]])
            '2024-03-15'
            >>> format_date_parts([[2024, 3]])
            '2024-03'
            >>> format_date_parts([[2024]])
            '2024'
            >>> format_date_parts(None)
            None
        """
        ...
