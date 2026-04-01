"""Deprecated PMID normalization compatibility service.

Deprecated: import pure helpers from
``bioetl.domain.normalization.identifiers`` instead.
Sunset target: 2026-06-30.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.normalization.identifiers import normalize_pmid

DEPRECATED_IN_FAVOR_OF = "bioetl.domain.normalization.identifiers.normalize_pmid"
SUNSET_DATE = "2026-06-30"

__all__ = [
    "PmidNormalizationService",
]


@dataclass(frozen=True, slots=True)
class PmidNormalizationService:
    """Normalize PubMed identifiers to canonical string format.

    Accepts int, str, or None. Rejects booleans, floats,
    empty strings, and non-positive values.
    """

    def normalize_pmid(self, pmid: str | int | None) -> str | None:
        """Normalize PubMed ID to string format. Returns None for invalid inputs.

        Args:
            pmid: PubMed identifier.

        Returns:
            Normalized PMID string, or None if invalid.
        """
        return normalize_pmid(pmid)
