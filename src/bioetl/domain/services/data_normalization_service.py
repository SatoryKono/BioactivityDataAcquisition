"""Cross-provider metadata normalizer (DataNormalizationPort implementation).

Scope — normalization of publication metadata fields that are shared across all
literature/bioactivity providers: author names, affiliations, DOIs, PMIDs,
publication dates, and free-text fields (titles, abstracts, OA status).

``DefaultDataNormalizer`` is the concrete implementation of
``DataNormalizationPort`` used throughout the pipeline. It is a pure facade:
all work is delegated to canonical ``bioetl.domain.normalization`` helpers.

Inheritance chain::

    AuthorNormalizationService          (author + affiliation logic)
        └── DefaultDataNormalizer  (adds DOI, PMID, date, text delegation)

Delegated helper modules:
- ``normalization.identifiers`` — DOI/PMID coercion
- ``normalization.dates`` — year validation, partial-date expansion,
  CrossRef date-parts formatting
- ``normalization.text`` — HTML stripping, whitespace normalization,
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

from bioetl.domain.normalization.dates import (
    format_date_parts as _format_date_parts,
)
from bioetl.domain.normalization.dates import (
    normalize_partial_date as _normalize_partial_date,
)
from bioetl.domain.normalization.dates import (
    validate_publication_year as _validate_publication_year,
)
from bioetl.domain.normalization.identifiers import (
    normalize_doi as _normalize_doi,
)
from bioetl.domain.normalization.identifiers import (
    normalize_pmid as _normalize_pmid,
)
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
from bioetl.domain.services.author_normalization_service import (
    AuthorNormalizationService,
)
from bioetl.domain.services.data_normalization_config import DataNormalizationConfig

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "DefaultDataNormalizer",
    "DefaultDataNormalizationService",
]


@dataclass(frozen=True, slots=True)
class DefaultDataNormalizer(AuthorNormalizationService):
    """Facade for data normalization, delegating to specialized services.

    Inherits author/affiliation normalization from AuthorNormalizationService.
    Delegates identifier, date, and text normalization to pure helper modules.
    Maintains backward-compatible API as per DataNormalizationPort.
    """

    config: DataNormalizationConfig = field(default_factory=DataNormalizationConfig)

    # --- DOI delegation ---

    def normalize_doi(self, doi: str | None) -> str | None:
        """Normalize DOI to lowercase, stripped format.

        Args:
            doi: DOI string in any supported format.

        Returns:
            Normalized bare DOI or None.
        """
        return _normalize_doi(doi)

    # --- PMID delegation ---

    def normalize_pmid(self, pmid: str | int | None) -> str | None:
        """Normalize PubMed ID to string format.

        Args:
            pmid: PubMed identifier.

        Returns:
            Normalized PMID string or None.
        """
        return _normalize_pmid(pmid)

    # --- Date delegation ---

    def normalize_year(self, year: int | None) -> tuple[int | None, bool]:
        """Validate publication year against configured range.

        Args:
            year: Publication year.

        Returns:
            Tuple of (year, is_warning).
        """
        return _validate_publication_year(
            year,
            min_year=self.config.min_publication_year,
            max_year=self.config.max_publication_year,
        )

    def normalize_partial_date(self, date_str: str | None) -> str | None:
        """Normalize partial date to full YYYY-MM-DD (end of period).

        Args:
            date_str: Date string in partial or full ISO format.

        Returns:
            Full ISO date string or None.
        """
        return _normalize_partial_date(date_str)

    def format_date_parts(
        self, date_parts: Sequence[Sequence[int]] | None
    ) -> str | None:
        """Format CrossRef date-parts to ISO YYYY-MM-DD.

        Args:
            date_parts: Date parts array.

        Returns:
            ISO date string or None.
        """
        return _format_date_parts(date_parts)

    # --- Text delegation ---

    def strip_html_tags(self, text: str | None) -> str | None:
        """Remove HTML tags, decode entities, normalize whitespace.

        Args:
            text: Input text string.

        Returns:
            Cleaned text or None.
        """
        return _strip_html_tags(text)

    def normalize_oa_status(self, status: str | None) -> str | None:
        """Normalize Open Access status to lowercase.

        Args:
            status: Status value.

        Returns:
            Normalized status or None.
        """
        return _normalize_oa_status(status)

    def normalize_string(self, value: str | None) -> str | None:
        """Normalize string by stripping whitespace.

        Args:
            value: Input value.

        Returns:
            Stripped string or None.
        """
        return _normalize_string(value)

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
        return _normalize_to_string(value)

    def normalize_title(self, title: str | None) -> str | None:
        """Normalize publication title.

        Args:
            title: Raw title string.

        Returns:
            Normalized title or None.
        """
        return _normalize_title(title)

    def normalize_abstract(self, abstract: str | None) -> str | None:
        """Normalize publication abstract.

        Args:
            abstract: Raw abstract string.

        Returns:
            Normalized abstract or None.
        """
        return _normalize_abstract(abstract)


# Deprecated compatibility alias retained during ADR-041 migration.
DefaultDataNormalizationService = DefaultDataNormalizer
