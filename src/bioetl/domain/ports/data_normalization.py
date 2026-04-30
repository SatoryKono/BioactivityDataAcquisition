"""Data normalization port interfaces (Protocols).

Defines contracts for text and data normalization operations:
- DOI normalization
- PMID normalization
- Year validation
- Author name normalization
- HTML tag stripping
- Open Access status normalization

This port handles text/data normalization, distinct from bioactivity
value normalization (unit conversion, pChEMBL, etc.).

All ports follow the Ports & Adapters pattern per RULES.md §1.1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "DataNormalizationPort",
]


@runtime_checkable
class DataNormalizationPort(Protocol):
    """Port for text and data normalization operations.

    Provides a unified interface for normalizing publication metadata,
    identifiers, and text content from various data sources.

    Example:
        >>> from bioetl.domain.services import DefaultDataNormalizer
        >>> normalizer = DefaultDataNormalizer()
        >>> normalizer.normalize_doi("10.1038/NATURE12373")
        '10.1038/nature12373'
    """

    def normalize_doi(self, doi: str | None) -> str | None:
        """Normalize DOI to lowercase, stripped format.

        Handles bare DOIs, https://doi.org/, http://doi.org/, and doi: prefixes.

        Args:
            doi: Digital Object Identifier.

        Returns:
            Normalized value.
        """
        ...

    def normalize_pmid(self, pmid: str | int | None) -> str | None:
        """Normalize PubMed ID to string format. Returns None for invalid inputs.

        Args:
            pmid: PubMed identifier.

        Returns:
            Normalized value.
        """
        ...

    def normalize_year(self, year: int | None) -> tuple[int | None, bool]:
        """Validate publication year against range [1500, 2100].

        Args:
            year: Publication year to validate.

        Returns:
            Tuple of (year, is_warning). Warning is True if year is outside
            valid range; year is set to None in that case.
        """
        ...

    def normalize_authors(
        self,
        authors: list[str] | str | None,
        salt: str,
    ) -> str | None:
        """Hash author names for PII protection. Accepts list, JSON, or delimited string.

        Args:
            authors: Author data in any supported format (list, JSON string, or delimited).
            salt: Cryptographic salt for PII hashing.

        Returns:
            JSON string of hashed author names, or None if no authors found.
        """
        ...

    def strip_html_tags(self, text: str | None) -> str | None:
        """Remove HTML tags, decode entities, normalize whitespace.

        Args:
            text: Input text string (may contain HTML tags and entities).

        Returns:
            Cleaned plain text, or None if input is None/empty.
        """
        ...

    def normalize_oa_status(self, status: str | None) -> str | None:
        """Normalize Open Access status to lowercase.

        Args:
            status: Status value.

        Returns:
            Normalized value.
        """
        ...

    def normalize_string(self, value: str | None) -> str | None:
        """Normalize string by stripping whitespace. Returns None if empty.

        Args:
            value: Input value.

        Returns:
            Normalized value.
        """
        ...

    def normalize_to_string(
        self,
        value: object,
    ) -> str | None:
        """Convert value to string, strip whitespace, return None if empty.

        Args:
            value: Input value.

        Returns:
            Normalized value.
        """
        ...

    def parse_authors_to_list(
        self,
        authors: list[str] | str | None,
    ) -> list[str]:
        """Parse author input (list, JSON, or delimited string) into a list of names.

        Args:
            authors: Author data as list of strings, JSON string, or
                delimited string (pipe/semicolon/comma).

        Returns:
            List of individual author name strings. Empty list if input is None.
        """
        ...

    def normalize_partial_date(self, date_str: str | None) -> str | None:
        """Normalize partial date to full YYYY-MM-DD (end of period strategy).

        Partial dates: YYYY-MM->YYYY-MM-last_day, YYYY->YYYY-12-31.
        Full dates remain unchanged.

        Args:
            date_str: Date str.

        Returns:
            Normalized value.
        """
        ...

    def format_date_parts(
        self,
        date_parts: Sequence[Sequence[int]] | None,
    ) -> str | None:
        """Format CrossRef date-parts to full YYYY-MM-DD (end of period strategy).

        Partial dates: [year,month]->YYYY-MM-last_day, [year]->YYYY-12-31.

        Args:
            date_parts: Nested sequences ``[[year, month, day]]`` as returned
                by CrossRef API.

        Returns:
            Formatted date string in YYYY-MM-DD format, or None if input is None.
        """
        ...

    def normalize_title(self, title: str | None) -> str | None:
        """Normalize publication title: HTML cleanup, whitespace, unicode NFC, trim.

        Args:
            title: Raw title string (may contain HTML tags, extra whitespace).

        Returns:
            Normalized title or None if input is None/empty.
        """
        ...

    def normalize_abstract(self, abstract: str | None) -> str | None:
        """Normalize publication abstract: HTML cleanup, whitespace, unicode NFC, trim.

        Args:
            abstract: Raw abstract string (may contain HTML tags, extra whitespace).

        Returns:
            Normalized abstract or None if input is None/empty.
        """
        ...

    def normalize_author_list(
        self,
        authors: list[str] | list[JsonDict] | str | None,
    ) -> str | None:
        """Parse and normalize author names to JSON string.

        Args:
            authors: Author data as list of strings, list of dicts with
                name fields, or JSON/delimited string.

        Returns:
            JSON string of normalized author names, or None if no authors found.
        """
        ...

    def normalize_author_keys(
        self,
        authors: list[str] | list[JsonDict] | str | None,
    ) -> str | None:
        """Normalize author names to short Surname_F keys (pipe-delimited).

        Args:
            authors: Author data as list of strings, list of dicts with
                name fields, or JSON/delimited string.

        Returns:
            Pipe-delimited string of ``Surname_F`` keys, or None if empty.
        """
        ...

    def normalize_affiliations(
        self,
        affiliations: list[str] | list[JsonDict] | None,
    ) -> str | None:
        """Extract, normalize, deduplicate affiliations to JSON string.

        Args:
            affiliations: Affiliation data as list of strings or list of
                dicts with affiliation fields.

        Returns:
            JSON string of unique normalized affiliations, or None if empty.
        """
        ...

    def extract_affiliations_from_authors(
        self,
        authors: list[JsonDict],
    ) -> list[str]:
        """Extract unique affiliations from author objects.

        Args:
            authors: List of author dicts, each potentially containing
                an ``affiliations`` key with affiliation data.

        Returns:
            Deduplicated list of affiliation strings extracted from authors.
        """
        ...
