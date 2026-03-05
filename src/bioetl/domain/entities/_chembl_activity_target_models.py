"""ChEMBL activity/target DTO facade with backward-compatible re-exports."""

from __future__ import annotations

from bioetl.domain.entities._chembl_activity_assay_models import (
    ActivityRecord,
    AssayRecord,
)
from bioetl.domain.entities._chembl_molecule_target_models import (
    MoleculeRecord,
    TargetRecord,
)

__all__ = [
    "ActivityRecord",
    "AssayRecord",
    "MoleculeRecord",
    "TargetRecord",
]
