"""Pydantic models for ChEMBL API responses.

This module is a backward-compatible facade that re-exports endpoint-specific
models from split modules and keeps the response/record mapping dictionaries.
"""

from __future__ import annotations

from pydantic import BaseModel

from bioetl.infrastructure.adapters.chembl.models_activity import (
    ActionType,
    ChemblActivityRecord,
    ChemblActivityResponse,
    LigandEfficiency,
)
from bioetl.infrastructure.adapters.chembl.models_additional import (
    ChemblCompoundRecordApiRecord,
    ChemblCompoundRecordResponse,
    ChemblProteinClassApiRecord,
    ChemblProteinClassResponse,
    ChemblPublicationSimilarityApiRecord,
    ChemblPublicationSimilarityResponse,
    ChemblTissueApiRecord,
    ChemblTissueResponse,
)
from bioetl.infrastructure.adapters.chembl.models_common import (
    ChemblAssayRecord,
    ChemblAssayResponse,
    ChemblCellLineRecord,
    ChemblCellLineResponse,
    ChemblPageMeta,
    ChemblPublicationApiRecord,
    ChemblPublicationResponse,
    ChemblReleaseInfo,
    ChemblTargetComponentRecord,
    ChemblTargetComponentResponse,
    ChemblTargetRecord,
    ChemblTargetResponse,
)
from bioetl.infrastructure.adapters.chembl.models_compound import (
    ChemblMoleculeRecord,
    ChemblMoleculeResponse,
    MoleculeHierarchy,
    MoleculeProperties,
    MoleculeStructures,
)

__all__ = [
    "CHEMBL_RECORD_MODELS",
    "CHEMBL_RESPONSE_MODELS",
    "ActionType",
    "ChemblActivityRecord",
    "ChemblActivityResponse",
    "ChemblAssayRecord",
    "ChemblAssayResponse",
    "ChemblCellLineRecord",
    "ChemblCellLineResponse",
    "ChemblCompoundRecordApiRecord",
    "ChemblCompoundRecordResponse",
    "ChemblMoleculeRecord",
    "ChemblMoleculeResponse",
    "ChemblPageMeta",
    "ChemblProteinClassApiRecord",
    "ChemblProteinClassResponse",
    "ChemblPublicationApiRecord",
    "ChemblPublicationResponse",
    "ChemblPublicationSimilarityApiRecord",
    "ChemblPublicationSimilarityResponse",
    "ChemblReleaseInfo",
    "ChemblTargetComponentRecord",
    "ChemblTargetComponentResponse",
    "ChemblTargetRecord",
    "ChemblTargetResponse",
    "ChemblTissueApiRecord",
    "ChemblTissueResponse",
    "LigandEfficiency",
    "MoleculeHierarchy",
    "MoleculeProperties",
    "MoleculeStructures",
]


CHEMBL_RESPONSE_MODELS: dict[str, type[BaseModel]] = {
    "activity": ChemblActivityResponse,
    "assay": ChemblAssayResponse,
    "molecule": ChemblMoleculeResponse,
    "compound": ChemblMoleculeResponse,
    "target": ChemblTargetResponse,
    "target_component": ChemblTargetComponentResponse,
    "publication": ChemblPublicationResponse,
    "document": ChemblPublicationResponse,
    "cell_line": ChemblCellLineResponse,
    "tissue": ChemblTissueResponse,
    "compound_record": ChemblCompoundRecordResponse,
    "protein_class": ChemblProteinClassResponse,
    "protein_classification": ChemblProteinClassResponse,
    "publication_similarity": ChemblPublicationSimilarityResponse,
    "document_similarity": ChemblPublicationSimilarityResponse,
}

CHEMBL_RECORD_MODELS: dict[str, type[BaseModel]] = {
    "activity": ChemblActivityRecord,
    "assay": ChemblAssayRecord,
    "molecule": ChemblMoleculeRecord,
    "compound": ChemblMoleculeRecord,
    "target": ChemblTargetRecord,
    "target_component": ChemblTargetComponentRecord,
    "publication": ChemblPublicationApiRecord,
    "document": ChemblPublicationApiRecord,
    "cell_line": ChemblCellLineRecord,
    "tissue": ChemblTissueApiRecord,
    "compound_record": ChemblCompoundRecordApiRecord,
    "protein_class": ChemblProteinClassApiRecord,
    "protein_classification": ChemblProteinClassApiRecord,
    "publication_similarity": ChemblPublicationSimilarityApiRecord,
    "document_similarity": ChemblPublicationSimilarityApiRecord,
}
