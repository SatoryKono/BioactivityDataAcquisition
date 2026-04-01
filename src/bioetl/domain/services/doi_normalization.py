"""Deprecated DOI normalization compatibility service.

Deprecated: import pure helpers from
``bioetl.domain.normalization.identifiers`` instead.
Sunset target: 2026-06-30.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.normalization.identifiers import normalize_doi

DEPRECATED_IN_FAVOR_OF = "bioetl.domain.normalization.identifiers.normalize_doi"
SUNSET_DATE = "2026-06-30"

__all__ = [
    "DoiNormalizationService",
]


@dataclass(frozen=True, slots=True)
class DoiNormalizationService:
    """Normalize DOI identifiers to canonical lowercase format.

    Handles DOIs in various formats:
    - Bare DOI: "10.1038/nature12373"
    - HTTPS URL: "https://doi.org/10.1038/nature12373"
    - HTTP URL: "http://doi.org/10.1038/nature12373"
    - doi: prefix: "doi:10.1038/nature12373"
    - DOI: prefix: "DOI:10.1038/nature12373"
    """

    def normalize_doi(self, doi: str | None) -> str | None:
        """Normalize DOI to canonical lowercase bare format.

        Args:
            doi: DOI string in any supported format.

        Returns:
            Normalized bare DOI (prefix removed, lowercase, stripped) or None.
        """
        return normalize_doi(doi)
