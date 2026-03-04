"""ChEMBL Tissue domain entity.

Represents tissue classification from ChEMBL database.
See: https://www.ebi.ac.uk/chembl/api/data/tissue
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.base import BaseEntity

__all__ = [
    "Tissue",
]


@dataclass(frozen=True, kw_only=True)
class Tissue(BaseEntity):
    """Represents a tissue type (ChEMBL Tissue).

    Tissues are anatomical structures used in assay experiments.
    They have 1:M relationship with Assay (via assay.tissue_id FK).

    Contains all fields from ChEMBL tissue API endpoint.
    See: https://www.ebi.ac.uk/chembl/api/data/tissue
    """

    # Primary identifier (REQUIRED)
    tissue_id: str

    # Core metadata (REQUIRED)
    pref_name: str

    # External ontology identifiers (API-OPTIONAL)
    bto_id: str | None = None  # BRENDA Tissue Ontology
    caloha_id: str | None = None  # CALIPHO tissue ontology
    efo_id: str | None = None  # Experimental Factor Ontology
    uberon_id: str | None = None  # Uberon multi-species anatomy ontology

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.tissue_id:
            raise ValueError("Tissue ChEMBL ID is required")
        if not self.pref_name:
            raise ValueError("Tissue pref_name is required")
