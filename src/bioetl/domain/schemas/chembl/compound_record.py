"""Pandera schema for ChEMBL Compound Record entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""
from __future__ import annotations

from datetime import date

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
    molregno: Series[int] | None = pa.Field(
        nullable=True, description="FK to molecule."
    )
    doc_id: Series[int] | None = pa.Field(
        nullable=True, description="FK to document."
    )

    # === Identifiers ===
    compound_key: Series[str] | None = pa.Field(
        nullable=True, description="Compound key."
    )
    compound_name: Series[str] | None = pa.Field(
        nullable=True, description="Compound name."
    )
    src_id: Series[int] | None = pa.Field(
        nullable=True, description="Source ID."
    )
    src_compound_id: Series[str] | None = pa.Field(
        nullable=True, description="Source compound ID."
    )
    src_compound_id_version: Series[int] | None = pa.Field(
        nullable=True, description="Source compound ID version."
    )

    # === Metadata ===
    filename: Series[str] | None = pa.Field(
        nullable=True, description="Filename."
    )
    load_date: Series[date] | None = pa.Field(
        nullable=True, description="Load date."
    )
    ridx: Series[str] | None = pa.Field(
        nullable=True, description="Record index."
    )
    cidx: Series[str] | None = pa.Field(
        nullable=True, description="Compound index."
    )
    molregno_comment: Series[str] | None = pa.Field(
        nullable=True, description="Molregno comment."
    )
    molregno_sv: Series[float] | None = pa.Field(
        nullable=True, description="Molregno SV."
    )

    # === Flags ===
    removed: Series[int] | None = pa.Field(
        nullable=True,
        isin=[0, 1],
        description="Removed flag.",
    )
    curated: Series[int] | None = pa.Field(
        nullable=True,
        isin=[0, 1],
        description="Curated flag.",
    )
    molregno_fixed: Series[int] | None = pa.Field(
        nullable=True,
        isin=[0, 1],
        description="Molregno fixed flag.",
    )

    class Config:
        """Pandera configuration."""
        strict = True
        ordered = True
        coerce = True
