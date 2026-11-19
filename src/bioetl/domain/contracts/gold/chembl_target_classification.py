"""Strict Gold contract 3.1.0; the legacy 3.0.0 model remains available."""

from __future__ import annotations

from bioetl.domain.contracts.gold._chembl_target_lookup_schemas import (
    ChEMBLTargetGoldSchema,
    ChEMBLTargetGoldSchemaV31,
    target_v31_schema_hash,
)
from bioetl.domain.entities.chembl_structures_foundation import Target
from bioetl.domain.entities.chembl_target_classification import TargetV31
from bioetl.domain.schemas.chembl.target import TargetSchema, TargetSchemaV31

__all__ = [
    "ChEMBLTargetGoldSchema",
    "ChEMBLTargetGoldSchemaV31",
    "Target",
    "TargetSchema",
    "TargetSchemaV31",
    "TargetV31",
    "target_v31_schema_hash",
]
