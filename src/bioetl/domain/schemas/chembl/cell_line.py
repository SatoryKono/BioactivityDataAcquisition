"""Pandera schema for ChEMBL Cell Line entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""
from __future__ import annotations

from typing import Optional

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
    cell_name: Optional[Series[str]] = pa.Field(
        nullable=True, description="Cell name."
    )
    cell_description: Optional[Series[str]] = pa.Field(
        nullable=True, description="Cell description."
    )
    cell_source_tissue: Optional[Series[str]] = pa.Field(
        nullable=True, description="Source tissue."
    )
    cell_source_organism: Optional[Series[str]] = pa.Field(
        nullable=True, description="Source organism."
    )
    cell_source_tax_id: Optional[Series[int]] = pa.Field(
        nullable=True, description="Source taxonomy ID."
    )

    # === External Identifiers ===
    clo_id: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_matches=r"^CLO:\d+$",
        description="CLO ID.",
    )
    efo_id: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_matches=r"^EFO:\d+$",
        description="EFO ID.",
    )
    cellosaurus_id: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_matches=r"^CVCL_\w+$",
        description="Cellosaurus ID.",
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
