"""ChEMBL Gold-layer contracts facade with backward-compatible re-exports."""

from __future__ import annotations

from bioetl.domain.contracts.gold._chembl_activity_assay_schemas import (
    ChEMBLActivityGoldSchema,
    ChEMBLAssayGoldSchema,
    ChEMBLAssayParametersGoldSchema,
)
from bioetl.domain.contracts.gold._chembl_molecule_target_schemas import (
    ChEMBLMoleculeGoldSchema,
    ChEMBLProteinClassGoldSchema,
    ChEMBLSubcellularFractionGoldSchema,
    ChEMBLTargetComponentGoldSchema,
    ChEMBLTargetGoldSchema,
    ChEMBLTargetProteinClassificationGoldSchema,
    ChEMBLTissueGoldSchema,
)
from bioetl.domain.contracts.gold._chembl_reference_publication_schemas import (
    ChEMBLCellLineGoldSchema,
    ChEMBLCompoundRecordGoldSchema,
    ChEMBLPublicationGoldSchema,
    ChEMBLPublicationSimilarityGoldSchema,
    ChEMBLPublicationTermGoldSchema,
)

__all__ = [
    "ChEMBLActivityGoldSchema",
    "ChEMBLAssayGoldSchema",
    "ChEMBLAssayParametersGoldSchema",
    "ChEMBLCellLineGoldSchema",
    "ChEMBLCompoundRecordGoldSchema",
    "ChEMBLMoleculeGoldSchema",
    "ChEMBLProteinClassGoldSchema",
    "ChEMBLPublicationGoldSchema",
    "ChEMBLPublicationSimilarityGoldSchema",
    "ChEMBLPublicationTermGoldSchema",
    "ChEMBLSubcellularFractionGoldSchema",
    "ChEMBLTargetComponentGoldSchema",
    "ChEMBLTargetGoldSchema",
    "ChEMBLTargetProteinClassificationGoldSchema",
    "ChEMBLTissueGoldSchema",
]
