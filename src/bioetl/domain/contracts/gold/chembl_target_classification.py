"""Strict Gold contracts 3.1.0 and 3.2.0; the legacy 3.0.0 model remains available."""

from __future__ import annotations

from bioetl.domain.contracts.gold._chembl_target_lookup_schemas import (
    ChEMBLTargetGoldSchema,
    ChEMBLTargetGoldSchemaV31,
    ChEMBLTargetGoldSchemaV32,
    target_v31_schema_hash,
    target_v32_schema_hash,
)
from bioetl.domain.entities.chembl_structures_foundation import Target
from bioetl.domain.entities.chembl_target_classification import TargetV31, TargetV32
from bioetl.domain.schemas.chembl.target import (
    TargetSchema,
    TargetSchemaV31,
    TargetSchemaV32,
)

__all__ = [
    "ChEMBLTargetGoldSchema",
    "ChEMBLTargetGoldSchemaV31",
    "ChEMBLTargetGoldSchemaV32",
    "Target",
    "TargetSchema",
    "TargetSchemaV31",
    "TargetSchemaV32",
    "TargetV31",
    "TargetV32",
    "target_v31_schema_hash",
    "target_v32_schema_hash",
]
