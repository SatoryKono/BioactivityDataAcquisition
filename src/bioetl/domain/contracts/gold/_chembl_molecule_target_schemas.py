"""ChEMBL molecule/target Gold-layer facade with backward-compatible re-exports."""

from __future__ import annotations

from bioetl.domain.contracts.gold._chembl_molecule_protein_schemas import (
    ChEMBLMoleculeGoldSchema,
    ChEMBLProteinClassGoldSchema,
)
from bioetl.domain.contracts.gold._chembl_target_lookup_schemas import (
    ChEMBLSubcellularFractionGoldSchema,
    ChEMBLTargetComponentGoldSchema,
    ChEMBLTargetGoldSchema,
    ChEMBLTargetProteinClassificationGoldSchema,
    ChEMBLTissueGoldSchema,
)

__all__ = [
    "ChEMBLMoleculeGoldSchema",
    "ChEMBLProteinClassGoldSchema",
    "ChEMBLSubcellularFractionGoldSchema",
    "ChEMBLTargetComponentGoldSchema",
    "ChEMBLTargetGoldSchema",
    "ChEMBLTargetProteinClassificationGoldSchema",
    "ChEMBLTissueGoldSchema",
]
