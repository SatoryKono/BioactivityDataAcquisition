"""Cross-provider metadata normalization service (DataNormalizationPort implementation).

Scope — normalization of publication metadata fields that are shared across all
literature/bioactivity providers: author names, affiliations, DOIs, PMIDs,
publication dates, and free-text fields (titles, abstracts, OA status).

``DefaultDataNormalizationService`` is the concrete implementation of
``DataNormalizationPort`` used throughout the pipeline.  It is a pure facade:
all work is delegated to single-responsibility sub-services.

Inheritance chain::

    AuthorNormalizationService          (author + affiliation logic)
        └── DefaultDataNormalizationService  (adds DOI, PMID, date, text delegation)

Delegated sub-services (all composed via dataclass fields):
- ``DoiNormalizationService``  — bare-DOI extraction / lowercasing
- ``PmidNormalizationService`` — PMID coercion to string
- ``DateNormalizationService`` — year validation, partial-date expansion,
                                  CrossRef date-parts formatting
- ``TextNormalizationService`` — HTML stripping, whitespace normalization,
                                  title / abstract cleaning

This service does **not** handle bioactivity scalars (IC50, Ki, pChEMBL, etc.).

Cross-reference
---------------
For ChEMBL-specific bioactivity scalar normalization (unit conversion,
pChEMBL calculation, potency classification, batch aggregation) see
:mod:`bioetl.domain.services.normalization_service`
(``NormalizationService``).

Pure domain service (no I/O) per RULES.md §1.1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.services.author_normalization_service import (
    AuthorNormalizationService,
)
from bioetl.domain.services.data_normalization_config import DataNormalizationConfig
from bioetl.domain.services.date_normalization import DateNormalizationService
from bioetl.domain.services.doi_normalization import DoiNormalizationService
from bioetl.domain.services.pmid_normalization import PmidNormalizationService
from bioetl.domain.services.text_normalization import TextNormalizationService

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "DefaultDataNormalizationService",
]


@dataclass(frozen=True, slots=True)
class DefaultDataNormalizationService(AuthorNormalizationService):
    """Facade for data normalization, delegating to specialized services.

    Inherits author/affiliation normalization from AuthorNormalizationService.
    Delegates identifier, date, and text normalization to dedicated services.
    Maintains backward-compatible API as per DataNormalizationPort.
    """

    config: DataNormalizationConfig = field(default_factory=DataNormalizationConfig)
    _doi: DoiNormalizationService = field(default_factory=DoiNormalizationService)
    _pmid: PmidNormalizationService = field(default_factory=PmidNormalizationService)
    _date: DateNormalizationService = field(init=False)
    _text: TextNormalizationService = field(default_factory=TextNormalizationService)

    def __post_init__(self) -> None:
        """Initialize DateNormalizationService with shared config."""
        object.__setattr__(self, "_date", DateNormalizationService(config=self.config))

    # --- DOI delegation ---

    def normalize_doi(self, doi: str | None) -> str | None:
        """Normalize DOI to lowercase, stripped format.

        Args:
            doi: DOI string in any supported format.

        Returns:
            Normalized bare DOI or None.
        """
        return self._doi.normalize_doi(doi)

    # --- PMID delegation ---

    def normalize_pmid(self, pmid: str | int | None) -> str | None:
        """Normalize PubMed ID to string format.

        Args:
            pmid: PubMed identifier.

        Returns:
            Normalized PMID string or None.
        """
        return self._pmid.normalize_pmid(pmid)

    # --- Date delegation ---

    def normalize_year(self, year: int | None) -> tuple[int | None, bool]:
        """Validate publication year against configured range.

        Args:
            year: Publication year.

        Returns:
            Tuple of (year, is_warning).
        """
        return self._date.normalize_year(year)

    def normalize_partial_date(self, date_str: str | None) -> str | None:
        """Normalize partial date to full YYYY-MM-DD (end of period).

        Args:
            date_str: Date string in partial or full ISO format.

        Returns:
            Full ISO date string or None.
        """
        return self._date.normalize_partial_date(date_str)

    def format_date_parts(
        self, date_parts: Sequence[Sequence[int]] | None
    ) -> str | None:
        """Format CrossRef date-parts to ISO YYYY-MM-DD.

        Args:
            date_parts: Date parts array.

        Returns:
            ISO date string or None.
        """
        return self._date.format_date_parts(date_parts)

    # --- Text delegation ---

    def strip_html_tags(self, text: str | None) -> str | None:
        """Remove HTML tags, decode entities, normalize whitespace.

        Args:
            text: Input text string.

        Returns:
            Cleaned text or None.
        """
        return self._text.strip_html_tags(text)

    def normalize_oa_status(self, status: str | None) -> str | None:
        """Normalize Open Access status to lowercase.

        Args:
            status: Status value.

        Returns:
            Normalized status or None.
        """
        return self._text.normalize_oa_status(status)

    def normalize_string(self, value: str | None) -> str | None:
        """Normalize string by stripping whitespace.

        Args:
            value: Input value.

        Returns:
            Stripped string or None.
        """
        return self._text.normalize_string(value)

    def normalize_to_string(
        self,
        value: object,
    ) -> str | None:
        """Convert value to string, strip whitespace, return None if empty.

        Args:
            value: Input value.

        Returns:
            String representation or None.
        """
        return self._text.normalize_to_string(value)

    def normalize_title(self, title: str | None) -> str | None:
        """Normalize publication title.

        Args:
            title: Raw title string.

        Returns:
            Normalized title or None.
        """
        return self._text.normalize_title(title)

    def normalize_abstract(self, abstract: str | None) -> str | None:
        """Normalize publication abstract.

        Args:
            abstract: Raw abstract string.

        Returns:
            Normalized abstract or None.
        """
        return self._text.normalize_abstract(abstract)
