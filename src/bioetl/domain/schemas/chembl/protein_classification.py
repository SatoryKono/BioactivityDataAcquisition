"""Pandera schema for ChEMBL Protein Classification entity.

Aligned with RULES.md v5.24 and ChEMBL 34 schema.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

__all__ = [
    "ProteinClassificationSchema",
]


class ProteinClassificationSchema(ETLRecordSchema):
    """Protein Classification validation schema for Silver layer."""

    # === Primary Key ===
    protein_class_id: Series[int] = pa.Field(
        nullable=False, unique=True, description="Primary key."
    )

    # === Foreign Keys ===
    parent_id: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="FK to parent classification."
    )
    replaced_by: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="FK to replacement classification."
    )

    # === Metadata ===
    pref_name: Series[str] | None = pa.Field(
        nullable=True, description="Preferred name."
    )
    short_name: Series[str] | None = pa.Field(nullable=True, description="Short name.")
    protein_class_desc: Series[str] | None = pa.Field(
        nullable=True, description="Description."
    )
    definition: Series[str] | None = pa.Field(nullable=True, description="Definition.")
    class_level: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        ge=1,
        description="Class level.",
    )
    sort_order: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Sort order."
    )

    # === Flags ===
    downgraded: Series[float] | None = pa.Field(
        nullable=True,
        isin=[0, 1],
        description="Downgraded flag.",
    )

    class Config:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
