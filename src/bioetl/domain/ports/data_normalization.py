"""Data normalization port interfaces (Protocols).

Defines contracts for text and data normalization operations:
- DOI normalization
- PMID normalization
- Year validation
- Author name normalization
- HTML tag stripping
- Open Access status normalization

All ports follow the Ports & Adapters pattern per RULES.md §1.1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence


@runtime_checkable
class DataNormalizationPort(Protocol):
    """Port for text and data normalization operations.

    Provides a unified interface for normalizing publication metadata,
    identifiers, and text content from various data sources.

    Example:
        >>> from bioetl.domain.services import DataNormalizationService
        >>> normalizer = DataNormalizationService()
        >>> normalizer.normalize_doi("10.1038/NATURE12373")
        '10.1038/nature12373'
    """

    def normalize_doi(self, doi: str | None) -> str | None:
        """Normalize DOI to lowercase, stripped format.

        Handles bare DOIs, https://doi.org/, http://doi.org/, and doi: prefixes.
        """
        ...

    def normalize_pmid(self, pmid: str | int | None) -> str | None:
        """Normalize PubMed ID to string format. Returns None for invalid inputs."""
        ...

    def normalize_year(self, year: int | None) -> tuple[int | None, bool]:
        """Validate publication year against range [1500, 2100].

        Returns (year, is_warning). Warning is True if year is outside valid range.
        """
        ...

    def normalize_authors(
        self,
        authors: list[str] | str | None,
        salt: str,
    ) -> str | None:
        """Hash author names for PII protection. Accepts list, JSON, or delimited string."""
        ...

    def strip_html_tags(self, text: str | None) -> str | None:
        """Remove HTML tags, decode entities, normalize whitespace."""
        ...

    def normalize_oa_status(self, status: str | None) -> str | None:
        """Normalize Open Access status to lowercase."""
        ...

    def normalize_string(self, value: str | None) -> str | None:
        """Normalize string by stripping whitespace. Returns None if empty."""
        ...

    def normalize_to_string(self, value: Any) -> str | None:
        """Convert value to string, strip whitespace, return None if empty."""
        ...

    def parse_authors_to_list(
        self,
        authors: list[str] | str | None,
    ) -> list[str]:
        """Parse author input (list, JSON, or delimited string) into a list of names."""
        ...

    def normalize_partial_date(self, date_str: str | None) -> str | None:
        """Normalize partial date to full YYYY-MM-DD (end of period strategy).

        Partial dates: YYYY-MM->YYYY-MM-30, YYYY->YYYY-12-31. Full dates unchanged.
        """
        ...

    def format_date_parts(
        self,
        date_parts: Sequence[Sequence[int]] | None,
    ) -> str | None:
        """Format CrossRef date-parts to full YYYY-MM-DD (end of period strategy).

        Partial dates: [year,month]->YYYY-MM-30, [year]->YYYY-12-31.
        """
        ...
