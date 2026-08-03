"""ChEMBL structural domain entities facade."""

from __future__ import annotations

from bioetl.domain.entities.chembl_structures_foundation import (
    CellLine,
    ChemblPublication,
    ChemblPublicationTerm,
    Target,
    TargetComponent,
    TargetProteinClassification,
)
from bioetl.domain.entities.chembl_structures_molecules import (
    ChemblPublicationSimilarity,
    Molecule,
    ProteinClassification,
)

__all__ = [
    "CellLine",
    "ChemblPublication",
    "ChemblPublicationSimilarity",
    "ChemblPublicationTerm",
    "Molecule",
    "ProteinClassification",
    "Target",
    "TargetComponent",
    "TargetProteinClassification",
]
