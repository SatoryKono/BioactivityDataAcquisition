"""Pandera schema for ChEMBL Compound Record entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class CompoundRecordSchema(ETLRecordSchema):
    """Compound Record validation schema for Silver layer."""

    # === Primary Key ===
    record_id: Series[int] = pa.Field(
        nullable=False, description="Primary key."
    )

    # === Foreign Keys ===
    molregno: Optional[Series[int]] = pa.Field(
        nullable=True, description="FK to molecule."
    )
    doc_id: Optional[Series[int]] = pa.Field(
        nullable=True, description="FK to document."
    )

    # === Identifiers ===
    compound_key: Optional[Series[str]] = pa.Field(
        nullable=True, description="Compound key."
    )
    compound_name: Optional[Series[str]] = pa.Field(
        nullable=True, description="Compound name."
    )
    src_id: Optional[Series[int]] = pa.Field(
        nullable=True, description="Source ID."
    )
    src_compound_id: Optional[Series[str]] = pa.Field(
        nullable=True, description="Source compound ID."
    )
    src_compound_id_version: Optional[Series[int]] = pa.Field(
        nullable=True, description="Source compound ID version."
    )

    # === Metadata ===
    filename: Optional[Series[str]] = pa.Field(
        nullable=True, description="Filename."
    )
    load_date: Optional[Series[date]] = pa.Field(
        nullable=True, description="Load date."
    )
    ridx: Optional[Series[str]] = pa.Field(
        nullable=True, description="Record index."
    )
    cidx: Optional[Series[str]] = pa.Field(
        nullable=True, description="Compound index."
    )
    molregno_comment: Optional[Series[str]] = pa.Field(
        nullable=True, description="Molregno comment."
    )
    molregno_sv: Optional[Series[float]] = pa.Field(
        nullable=True, description="Molregno SV."
    )

    # === Flags ===
    removed: Optional[Series[int]] = pa.Field(
        nullable=True,
        isin=[0, 1],
        description="Removed flag.",
    )
    curated: Optional[Series[int]] = pa.Field(
        nullable=True,
        isin=[0, 1],
        description="Curated flag.",
    )
    molregno_fixed: Optional[Series[int]] = pa.Field(
        nullable=True,
        isin=[0, 1],
        description="Molregno fixed flag.",
    )

    class Config:
        """Pandera configuration."""
        strict = True
        ordered = True
        coerce = True
