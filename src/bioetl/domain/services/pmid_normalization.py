"""PMID normalization service.

Pure domain service (no I/O) per RULES.md §1.1.
Handles normalization of PubMed identifiers.
"""

from __future__ import annotations

from dataclasses import dataclass

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
        str_value = self._pmid_to_string(pmid)
        return self._validate_pmid_string(str_value) if str_value else None

    @staticmethod
    def _pmid_to_string(pmid: str | int | None) -> str | None:
        """Convert PMID to string, rejecting invalid types."""
        if pmid is None or isinstance(pmid, bool):
            return None
        if isinstance(pmid, (int, str)):
            result = str(pmid).strip()
            return result if result else None
        return None

    @staticmethod
    def _validate_pmid_string(str_value: str) -> str | None:
        """Validate and normalize PMID string."""
        if not str_value.isdigit():
            return None
        int_value = int(str_value)
        return str(int_value) if int_value > 0 else None
