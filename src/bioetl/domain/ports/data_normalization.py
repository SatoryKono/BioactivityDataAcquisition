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

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

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
        >>> from bioetl.domain.services import DataNormalizationService
from bioetl.domain.types import JsonDict
        >>> normalizer = DataNormalizationService()
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

        Returns (year, is_warning). Warning is True if year is outside valid range.

        Args:
            year: Year.

        Returns:
            Normalized value.
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
            text: Input text string.

        Returns:
            The str | None result.
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
        value: Any,  # Any: port contract accepts any attribute value
    ) -> str | None:  # Any: port contract accepts any attribute value
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
            authors: Authors.

        Returns:
            Parsed result.
        """
        ...

    def normalize_partial_date(self, date_str: str | None) -> str | None:
        """Normalize partial date to full YYYY-MM-DD (end of period strategy).

        Partial dates: YYYY-MM->YYYY-MM-30, YYYY->YYYY-12-31. Full dates unchanged.

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

        Partial dates: [year,month]->YYYY-MM-30, [year]->YYYY-12-31.

        Args:
            date_parts: Date parts.

        Returns:
            The str | None result.
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
        authors: list[str]
        | list[JsonDict]  # Any: port contract allows heterogeneous record values
        | str
        | None,  # Any: port contract allows heterogeneous record values
    ) -> str | None:
        """Parse and normalize author names to JSON string.

        Args:
            authors: Authors.

        Returns:
            Normalized value.
        """
        ...

    def normalize_author_keys(
        self,
        authors: list[str]
        | list[JsonDict]  # Any: port contract allows heterogeneous record values
        | str
        | None,  # Any: port contract allows heterogeneous record values
    ) -> str | None:
        """Normalize author names to short Surname_F keys (pipe-delimited).

        Args:
            authors: Authors.

        Returns:
            Normalized value.
        """
        ...

    def normalize_affiliations(
        self,
        affiliations: list[str]
        | list[JsonDict]  # Any: port contract allows heterogeneous record values
        | None,  # Any: port contract allows heterogeneous record values
    ) -> str | None:
        """Extract, normalize, deduplicate affiliations to JSON string.

        Args:
            affiliations: Affiliations.

        Returns:
            Normalized value.
        """
        ...

    def extract_affiliations_from_authors(
        self,
        authors: list[
            JsonDict  # Any: port contract allows heterogeneous record values
        ],  # Any: port contract allows heterogeneous record values
    ) -> list[str]:
        """Extract unique affiliations from author objects.

        Args:
            authors: Authors.

        Returns:
            Extracted value.
        """
        ...
