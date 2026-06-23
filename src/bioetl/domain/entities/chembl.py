"""ChEMBL DTO facade with backward-compatible re-exports."""

from __future__ import annotations

from bioetl.domain.entities._chembl_activity_target_models import (
    ActivityRecord,
    AssayRecord,
    MoleculeRecord,
    TargetRecord,
)
from bioetl.domain.entities._chembl_additional_models import (
    CompoundLinkRecord,
    PublicationSimilarityRecord,
    TissueRecord,
)
from bioetl.domain.entities._chembl_reference_models import (
    CellLineRecord,
    ChemblPublicationRecord,
    ChemblPublicationTermRecord,
    ProteinClassRecord,
    TargetComponentRecord,
)

__all__ = [
    "ActivityRecord",
    "AssayRecord",
    "CellLineRecord",
    "ChemblPublicationRecord",
    "ChemblPublicationTermRecord",
    "CompoundLinkRecord",
    "MoleculeRecord",
    "ProteinClassRecord",
    "PublicationSimilarityRecord",
    "TargetComponentRecord",
    "TargetRecord",
    "TissueRecord",
]
