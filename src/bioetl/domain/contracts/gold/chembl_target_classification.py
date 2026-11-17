"""Strict Gold contract 3.1.0; the legacy 3.0.0 model remains available."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import cast

from bioetl.domain.contracts.gold._chembl_target_lookup_schemas import (
    ChEMBLTargetGoldSchema,
    Series,
    pa,
)
from bioetl.domain.transformations import canonical_json_dumps
from bioetl.domain.types import JsonDict


class ChEMBLTargetGoldSchemaV31(ChEMBLTargetGoldSchema):
    """Require the complete additive column shape while allowing no assignment."""

    iuphar_target_id: Series[str] = pa.Field(nullable=True)
    iuphar_class: Series[str] = pa.Field(nullable=True)
    iuphar_match_status: Series[str] = pa.Field(nullable=True)
    iuphar_annotation_status: Series[str] = pa.Field(nullable=True)
    local_class: Series[str] = pa.Field(nullable=True)
    effective_class: Series[str] = pa.Field(nullable=True)
    effective_source: Series[str] = pa.Field(nullable=True)
    decision_status: Series[str] = pa.Field(nullable=True)
    target_class_profile_sha256: Series[str] = pa.Field(
        nullable=True, str_matches=r"^[0-9a-f]{64}$"
    )


def target_v31_schema_hash() -> str:
    """Bind manifested identity to the actual canonical V31 schema model."""
    render_schema = cast(
        "Callable[[], JsonDict]", ChEMBLTargetGoldSchemaV31.to_json_schema
    )
    canonical = canonical_json_dumps(render_schema())
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = ["ChEMBLTargetGoldSchemaV31", "target_v31_schema_hash"]
