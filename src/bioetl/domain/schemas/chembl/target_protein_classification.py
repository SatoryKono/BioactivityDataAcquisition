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
    classification_status: Series[str] = pa.Field(
        nullable=False,
        isin=["resolved", "missing_classification", "quarantined"],
        description="Resolution status for this target classification row.",
    )
    component_id: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        description="Target component ID that supplied the classification.",
    )
    leaf_id: Series[str] | None = pa.Field(
        nullable=True,
        description="Resolved leaf protein classification ID.",
    )
    l1_id: Series[str] | None = pa.Field(
        nullable=True, description="Level 1 protein classification ID."
    )
    l1_name: Series[str] | None = pa.Field(
        nullable=True, description="Level 1 protein classification name."
    )
    l1_desc: Series[str] | None = pa.Field(
        nullable=True, description="Level 1 protein classification description."
    )
    l2_id: Series[str] | None = pa.Field(
        nullable=True, description="Level 2 protein classification ID."
    )
    l2_name: Series[str] | None = pa.Field(
        nullable=True, description="Level 2 protein classification name."
    )
    l2_desc: Series[str] | None = pa.Field(
        nullable=True, description="Level 2 protein classification description."
    )
    l3_id: Series[str] | None = pa.Field(
        nullable=True, description="Level 3 protein classification ID."
    )
    l3_name: Series[str] | None = pa.Field(
        nullable=True, description="Level 3 protein classification name."
    )
    l3_desc: Series[str] | None = pa.Field(
        nullable=True, description="Level 3 protein classification description."
    )
    l4_id: Series[str] | None = pa.Field(
        nullable=True, description="Level 4 protein classification ID."
    )
    l4_name: Series[str] | None = pa.Field(
        nullable=True, description="Level 4 protein classification name."
    )
    l4_desc: Series[str] | None = pa.Field(
        nullable=True, description="Level 4 protein classification description."
    )
    l5_id: Series[str] | None = pa.Field(
        nullable=True, description="Level 5 protein classification ID."
    )
    l5_name: Series[str] | None = pa.Field(
        nullable=True, description="Level 5 protein classification name."
    )
    l5_desc: Series[str] | None = pa.Field(
        nullable=True, description="Level 5 protein classification description."
    )
    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
