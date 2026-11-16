"""Strict Gold contract 3.1.0; the legacy 3.0.0 model remains available."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold import ChEMBLTargetGoldSchema


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


__all__ = ["ChEMBLTargetGoldSchemaV31"]
