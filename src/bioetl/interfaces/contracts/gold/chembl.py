"""ChEMBL Gold layer data contracts.

DEPRECATED: This module re-exports schemas from bioetl.domain.contracts.gold.chembl for
backward compatibility. New code should import from bioetl.domain.contracts.gold.chembl.

Contains Pandera DataFrameModel schemas for ChEMBL entities in the Gold layer:
- Activity: Bioassay activity records with molecule-target-assay relationships
- Assay: Bioassay protocols and parameters
- AssayParameters: Experimental assay parameters (concentrations, pH, temperature)
- CellLine: Cell line metadata
- CompoundRecord: Document-molecule linkages
- Document (Publication): Publication records
- DocumentSimilarity: Document similarity (Tanimoto coefficients)
- DocumentTerm: Document-term associations (flattened 1:M relationship)
- Molecule: Chemical structures with properties
- ProteinClass: Hierarchical protein classifications
- Target: Protein targets with taxonomic info
- TargetComponent: Target protein components

Int→Float coercion note:
    Fields marked with `coerce=True` and `Series[float]` that are `int64` in Silver
    use float to handle nullable integers. This is a deliberate design decision
    documented in RULES.md §2.6.
"""

from __future__ import annotations

# Re-export all schemas from domain.contracts for backward compatibility
from bioetl.domain.contracts.gold.chembl import (
    ChEMBLActivityGoldSchema,
    ChEMBLAssayGoldSchema,
    ChEMBLAssayParametersGoldSchema,
    ChEMBLCellLineGoldSchema,
    ChEMBLCompoundRecordGoldSchema,
    ChEMBLDocumentGoldSchema,
    ChEMBLDocumentSimilarityGoldSchema,
    ChEMBLDocumentTermGoldSchema,
    ChEMBLMoleculeGoldSchema,
    ChEMBLProteinClassGoldSchema,
    ChEMBLTargetComponentGoldSchema,
    ChEMBLTargetGoldSchema,
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
    "ChEMBLTargetComponentGoldSchema",
    "ChEMBLTargetGoldSchema",
]
