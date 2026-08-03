"""ChEMBL Compound Record domain entity.

Contains the CompoundRecord entity which links molecules to documents.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.base import BaseEntity

__all__ = [
    "CompoundRecord",
]


@dataclass(frozen=True, kw_only=True)
class CompoundRecord(BaseEntity):
    """Represents a compound record (ChEMBL Compound Record).

    A compound record links a molecule to a document, representing the
    occurrence of a compound in a specific publication with its original name.

    Contains all fields from ChEMBL compound_record API endpoint.
    See: https://www.ebi.ac.uk/chembl/api/data/compound_record
    """

    # Primary identifier (REQUIRED, surrogate key from ChEMBL)
    record_id: int

    # Foreign keys (REQUIRED)
    molecule_id: str
    publication_id: str

    # Original names from the document (API-OPTIONAL)
    compound_key: str | None = None
    compound_name: str | None = None

    # Source information (REQUIRED for src_id, OPTIONAL for src_compound_id)
    src_id: int
    src_compound_id: str | None = None

    def _validate_invariants(self) -> None:
        """Validate CompoundRecord invariants.

        Validates required fields and positive integer constraints.
        Uses simplified checks: int < 1 covers 0 and negatives.
        """
        self._validate_positive_id(self.record_id, "record_id")
        self._validate_positive_id(self.src_id, "src_id")
        self._validate_required_str(self.molecule_id, "molecule_id")
        self._validate_required_str(self.publication_id, "publication_id")

    def _validate_positive_id(self, value: int, field_name: str) -> None:
        """Validate that an ID is positive (> 0)."""
        if value < 1:
            raise ValueError(f"{field_name} must be > 0, got {value}")

    def _validate_required_str(self, value: str, field_name: str) -> None:
        """Validate that a string field is non-empty."""
        if not value:
            raise ValueError(f"{field_name} is required")
