"""Pandera schema for ChEMBL Target Component entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import TARGET_COMPONENT_RELATIONSHIPS


class TargetComponentSchema(ETLRecordSchema):
    """Target Component validation schema for Silver layer."""

    # === Primary Key ===
    targcomp_id: Series[int] = pa.Field(nullable=False, description="Primary key.")

    # === Foreign Keys ===
    tid: Series[int] = pa.Field(nullable=False, description="FK to target.")
    component_id: Series[int] = pa.Field(
        nullable=False, description="FK to component_sequences."
    )

    # === Metadata ===
    relationship: Series[str] | None = pa.Field(
        nullable=True,
        isin=list(TARGET_COMPONENT_RELATIONSHIPS),
        description="Relationship type.",
    )
    stoichiometry: Series[int] | None = pa.Field(
        nullable=True,
        ge=1,
        description="Stoichiometry.",
    )
    homologue: Series[int] | None = pa.Field(
        nullable=True,
        isin=[0, 1, 2],
        description="Homologue flag.",
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
