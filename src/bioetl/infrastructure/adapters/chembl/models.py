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
    "ChemblMoleculeRecord",
    "ChemblMoleculeResponse",
    "ChemblPageMeta",
    "ChemblPublicationApiRecord",
    "ChemblPublicationResponse",
    "ChemblReleaseInfo",
    "ChemblTargetComponentRecord",
    "ChemblTargetComponentResponse",
    "ChemblTargetRecord",
    "ChemblTargetResponse",
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
    "document": ChemblPublicationResponse,
    "cell_line": ChemblCellLineResponse,
}

CHEMBL_RECORD_MODELS: dict[str, type[BaseModel]] = {
    "activity": ChemblActivityRecord,
    "assay": ChemblAssayRecord,
    "molecule": ChemblMoleculeRecord,
    "compound": ChemblMoleculeRecord,
    "target": ChemblTargetRecord,
    "target_component": ChemblTargetComponentRecord,
    "document": ChemblPublicationApiRecord,
    "cell_line": ChemblCellLineRecord,
}
