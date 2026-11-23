"""Strict Gold contract 3.1.0; the legacy 3.0.0 model remains available."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import cast

from bioetl.domain.contracts.gold._chembl_target_lookup_schemas import (
    ChEMBLTargetGoldSchema,
    ChEMBLTargetGoldSchemaV31,
    Series,
    pa,
    target_v31_schema_hash,
)
from bioetl.domain.entities.chembl_structures_foundation import Target
from bioetl.domain.entities.chembl_target_classification import TargetV31, TargetV32
from bioetl.domain.schemas.chembl.target import (
    TargetSchema,
    TargetSchemaV31,
    TargetSchemaV32,
)
from bioetl.domain.transformations import canonical_json_dumps
from bioetl.domain.types import JsonDict


class ChEMBLTargetGoldSchemaV32(ChEMBLTargetGoldSchemaV31):
    """Persist subclass, path and evidence detail without removing V31 columns."""

    iuphar_type_raw: Series[str] = pa.Field(nullable=True)
    iuphar_annotation_capability: Series[str] = pa.Field(nullable=True)
    iuphar_family_ids: Series[str] = pa.Field(nullable=True)
    iuphar_subclasses: Series[str] = pa.Field(nullable=True)
    iuphar_paths: Series[str] = pa.Field(nullable=True)
    local_status: Series[str] = pa.Field(nullable=True)
    local_subclasses: Series[str] = pa.Field(nullable=True)
    local_rule_ids: Series[str] = pa.Field(nullable=True)
    effective_subclasses: Series[str] = pa.Field(nullable=True)
    conflict_codes: Series[str] = pa.Field(nullable=True)
    classification_evidence_ids: Series[str] = pa.Field(nullable=True)


def target_v32_schema_hash() -> str:
    """Bind manifested identity to the actual canonical V32 schema model."""
    render_schema = cast(
        "Callable[[], JsonDict]", ChEMBLTargetGoldSchemaV32.to_json_schema
    )
    canonical = canonical_json_dumps(render_schema())
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
