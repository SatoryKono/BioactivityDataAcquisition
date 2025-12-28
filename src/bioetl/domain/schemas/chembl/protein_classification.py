"""Pandera schema for ChEMBL Protein Classification entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""
from __future__ import annotations

from typing import Optional

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class ProteinClassificationSchema(ETLRecordSchema):
    """Protein Classification validation schema for Silver layer."""

    # === Primary Key ===
    protein_class_id: Series[int] = pa.Field(
        nullable=False, description="Primary key."
    )

    # === Foreign Keys ===
    parent_id: Optional[Series[int]] = pa.Field(
        nullable=True, description="FK to parent classification."
    )
    replaced_by: Optional[Series[int]] = pa.Field(
        nullable=True, description="FK to replacement classification."
    )

    # === Metadata ===
    pref_name: Optional[Series[str]] = pa.Field(
        nullable=True, description="Preferred name."
    )
    short_name: Optional[Series[str]] = pa.Field(
        nullable=True, description="Short name."
    )
    protein_class_desc: Optional[Series[str]] = pa.Field(
        nullable=True, description="Description."
    )
    definition: Optional[Series[str]] = pa.Field(
        nullable=True, description="Definition."
    )
    class_level: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=1,
        description="Class level.",
    )
    sort_order: Optional[Series[int]] = pa.Field(
        nullable=True, description="Sort order."
    )

    # === Flags ===
    downgraded: Optional[Series[int]] = pa.Field(
        nullable=True,
        isin=[0, 1],
        description="Downgraded flag.",
    )

    class Config:
        """Pandera configuration."""
        strict = True
        ordered = True
        coerce = True
