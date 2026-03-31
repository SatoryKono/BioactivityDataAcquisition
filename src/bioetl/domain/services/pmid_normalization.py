"""PMID normalization service.

Pure domain service (no I/O) per RULES.md §1.1.
Handles normalization of PubMed identifiers.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.normalization.identifiers import normalize_pmid

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
