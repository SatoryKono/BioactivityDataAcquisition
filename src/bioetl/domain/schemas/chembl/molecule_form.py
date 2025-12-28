"""Pandera schema for ChEMBL Molecule Form entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""
from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class MoleculeFormSchema(ETLRecordSchema):
    """Molecule Form validation schema for Silver layer."""

    # === Primary Key ===
    molregno: Series[int] = pa.Field(
        nullable=False, description="Primary key (child molecule)."
    )

    # === Foreign Keys ===
    parent_molregno: Series[int] | None = pa.Field(
        nullable=True, description="FK to parent molecule."
    )
    active_molregno: Series[int] | None = pa.Field(
        nullable=True, description="FK to active molecule."
    )

    class Config:
        """Pandera configuration."""
        strict = True
        ordered = True
        coerce = True
