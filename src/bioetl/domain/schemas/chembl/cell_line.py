"""Pandera schema for ChEMBL Cell Line entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""
from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class CellLineSchema(ETLRecordSchema):
    """Cell Line validation schema for Silver layer."""

    # === Primary Key ===
    cell_id: Series[int] = pa.Field(
        nullable=False, description="Primary key."
    )

    # === Metadata ===
    cell_name: Series[str] | None = pa.Field(
        nullable=True, description="Cell name."
    )
    cell_description: Series[str] | None = pa.Field(
        nullable=True, description="Cell description."
    )
    cell_source_tissue: Series[str] | None = pa.Field(
        nullable=True, description="Source tissue."
    )
    cell_source_organism: Series[str] | None = pa.Field(
        nullable=True, description="Source organism."
    )
    cell_source_tax_id: Series[int] | None = pa.Field(
        nullable=True, description="Source taxonomy ID."
    )

    # === External Identifiers ===
    clo_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CLO:\d+$",
        description="CLO ID.",
    )
    efo_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^EFO:\d+$",
        description="EFO ID.",
    )
    cellosaurus_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CVCL_\w+$",
        description="Cellosaurus ID.",
    )

    # === Flags ===
    downgraded: Series[int] | None = pa.Field(
        nullable=True,
        isin=[0, 1],
        description="Downgraded flag.",
    )

    class Config:
        """Pandera configuration."""
        strict = True
        ordered = True
        coerce = True
