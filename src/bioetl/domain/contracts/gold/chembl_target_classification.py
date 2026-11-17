"""Strict Gold contract 3.1.0; the legacy 3.0.0 model remains available."""

from __future__ import annotations

from bioetl.domain.contracts.gold._chembl_target_lookup_schemas import (
    ChEMBLTargetGoldSchemaV31,
    target_v31_schema_hash,
)

__all__ = ["ChEMBLTargetGoldSchemaV31", "target_v31_schema_hash"]
