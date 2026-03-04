"""DOI normalization service.

Pure domain service (no I/O) per RULES.md §1.1.
Handles normalization of Digital Object Identifiers.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "DoiNormalizationService",
]

_DOI_URL_PREFIXES = ("https://doi.org/", "http://doi.org/", "doi:")


@dataclass(frozen=True, slots=True)
class DoiNormalizationService:
    """Normalize DOI identifiers to canonical lowercase format.

    Handles DOIs in various formats:
    - Bare DOI: "10.1038/nature12373"
    - HTTPS URL: "https://doi.org/10.1038/nature12373"
    - HTTP URL: "http://doi.org/10.1038/nature12373"
    - doi: prefix: "doi:10.1038/nature12373"
    """

    def normalize_doi(self, doi: str | None) -> str | None:
        """Normalize DOI to lowercase, stripped format.

        Args:
            doi: DOI string in any supported format.

        Returns:
            Normalized bare DOI (lowercase, stripped) or None if input is None/empty.
        """
        if not doi:
            return None
        stripped = self._strip_doi_prefix(doi)
        result = stripped.strip().lower()
        return result if result else None

    @staticmethod
    def _strip_doi_prefix(doi: str) -> str:
        """Strip known DOI URL prefixes (https://doi.org/, http://doi.org/, doi:)."""
        for prefix in _DOI_URL_PREFIXES:
            if doi.startswith(prefix):
                return doi[len(prefix) :]
        return doi
