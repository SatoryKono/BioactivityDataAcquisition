"""ChEMBL DTO facade with backward-compatible re-exports."""

from __future__ import annotations

from bioetl.domain.entities._chembl_activity_target_models import (
    ActivityRecord,
    AssayRecord,
    MoleculeRecord,
    TargetRecord,
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
    "MoleculeRecord",
    "ProteinClassRecord",
    "TargetComponentRecord",
    "TargetRecord",
]
