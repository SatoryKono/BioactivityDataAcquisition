"""PubChem domain entities.

Contains entities for PubChem data: Compound.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class Compound(BaseEntity):
    """Represents a chemical compound (PubChem Compound)."""

    cid: str
    molecular_formula: str | None = None
    molecular_weight: str | None = None  # Kept as string to preserve precision/format

    # Structure representations
    canonical_smiles: str | None = None
    isomeric_smiles: str | None = None
    inchi: str | None = None
    inchikey: str | None = None
    iupac_name: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.cid:
            raise ValueError("Compound CID is required")

        # Invariant: At least one structural representation should be present
        if not any([self.canonical_smiles, self.isomeric_smiles, self.inchi]):
            raise ValueError(
                "Compound must have at least one structural identifier (SMILES/InChI)"
            )
