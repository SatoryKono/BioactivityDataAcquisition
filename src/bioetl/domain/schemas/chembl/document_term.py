"""Pandera schema for ChEMBL Document Term entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class DocumentTermSchema(ETLRecordSchema):
    """Document Term validation schema for Silver layer."""

    # === Primary Key ===
    id: Series[int] = pa.Field(nullable=False, description="Primary key.")

    # === Metadata ===
    term: Series[str] | None = pa.Field(nullable=True, description="Term.")

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
