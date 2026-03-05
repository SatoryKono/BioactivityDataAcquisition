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
    ChEMBLTissueGoldSchema,
)
from bioetl.domain.contracts.gold._chembl_reference_publication_schemas import (
    ChEMBLCellLineGoldSchema,
    ChEMBLCompoundRecordGoldSchema,
    ChEMBLDocumentGoldSchema,
    ChEMBLDocumentSimilarityGoldSchema,
    ChEMBLDocumentTermGoldSchema,
)

__all__ = [
    "ChEMBLActivityGoldSchema",
    "ChEMBLAssayGoldSchema",
    "ChEMBLAssayParametersGoldSchema",
    "ChEMBLCellLineGoldSchema",
    "ChEMBLCompoundRecordGoldSchema",
    "ChEMBLDocumentGoldSchema",
    "ChEMBLDocumentSimilarityGoldSchema",
    "ChEMBLDocumentTermGoldSchema",
    "ChEMBLMoleculeGoldSchema",
    "ChEMBLProteinClassGoldSchema",
    "ChEMBLSubcellularFractionGoldSchema",
    "ChEMBLTargetComponentGoldSchema",
    "ChEMBLTargetGoldSchema",
    "ChEMBLTissueGoldSchema",
]
