"""Pandera schema for ChEMBL Target Component entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""
from __future__ import annotations

from typing import Optional

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class TargetComponentSchema(ETLRecordSchema):
    """Target Component validation schema for Silver layer."""

    # === Primary Key ===
    targcomp_id: Series[int] = pa.Field(
        nullable=False, description="Primary key."
    )

    # === Foreign Keys ===
    tid: Series[int] = pa.Field(
        nullable=False, description="FK to target."
    )
    component_id: Series[int] = pa.Field(
        nullable=False, description="FK to component_sequences."
    )

    # === Metadata ===
    relationship: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=["SINGLE PROTEIN", "PROTEIN SUBUNIT", "RNA", "INTERACTING PROTEIN"],
        description="Relationship type.",
    )
    stoichiometry: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=1,
        description="Stoichiometry.",
    )
    homologue: Optional[Series[int]] = pa.Field(
        nullable=True,
        isin=[0, 1, 2],
        description="Homologue flag.",
    )

    class Config:
        """Pandera configuration."""
        strict = True
        ordered = True
        coerce = True
