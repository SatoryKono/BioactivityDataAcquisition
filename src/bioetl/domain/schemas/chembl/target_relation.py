"""Pandera schema for ChEMBL Target Relation entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class TargetRelationSchema(ETLRecordSchema):
    """Target Relation validation schema for Silver layer."""

    # === Primary Key ===
    targrel_id: Series[int] = pa.Field(nullable=False, description="Primary key.")

    # === Foreign Keys ===
    tid: Series[int] = pa.Field(nullable=False, description="FK to target.")
    related_tid: Series[int] = pa.Field(
        nullable=False, description="FK to related target."
    )

    # === Metadata ===
    relationship: Series[str] | None = pa.Field(
        nullable=True,
        isin=["EQUIVALENT TO", "SUBSET OF", "SUPERSET OF", "OVERLAPS WITH"],
        description="Relationship type.",
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
