"""Pandera schema for derived ChEMBL target protein classifications."""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

__all__ = ["TargetProteinClassificationSchema"]


class TargetProteinClassificationSchema(ETLRecordSchema):
    """Derived target-to-protein-classification relation schema."""

    target_id: Series[str] = pa.Field(nullable=False, description="ChEMBL target ID.")
    component_id: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        description="Target component ID that supplied the classification.",
    )
    hierarchy_index: Series[int] = pa.Field(
        nullable=False,
        ge=0,
        description="Deterministic per-target hierarchy ordinal.",
    )
    leaf_id: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        description="Resolved leaf protein classification ID.",
    )
    l1_id: Series[pd.Int64Dtype] | None = pa.Field(nullable=True)
    l1_name: Series[str] | None = pa.Field(nullable=True)
    l1_desc: Series[str] | None = pa.Field(nullable=True)
    l2_id: Series[pd.Int64Dtype] | None = pa.Field(nullable=True)
    l2_name: Series[str] | None = pa.Field(nullable=True)
    l2_desc: Series[str] | None = pa.Field(nullable=True)
    l3_id: Series[pd.Int64Dtype] | None = pa.Field(nullable=True)
    l3_name: Series[str] | None = pa.Field(nullable=True)
    l3_desc: Series[str] | None = pa.Field(nullable=True)
    l4_id: Series[pd.Int64Dtype] | None = pa.Field(nullable=True)
    l4_name: Series[str] | None = pa.Field(nullable=True)
    l4_desc: Series[str] | None = pa.Field(nullable=True)
    l5_id: Series[pd.Int64Dtype] | None = pa.Field(nullable=True)
    l5_name: Series[str] | None = pa.Field(nullable=True)
    l5_desc: Series[str] | None = pa.Field(nullable=True)
    classification_status: Series[str] = pa.Field(
        nullable=False,
        isin=["resolved", "missing_classification", "quarantined"],
        description="Resolution status for this target classification row.",
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
