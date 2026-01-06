"""Pandera schema for UniProt Isoform entity.

Aligned with RULES.md v5.0 and UniProt REST API.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

# === Fixed Value Constants ===
SEQUENCE_STATUSES = ["displayed", "described", "not described", "external"]


class IsoformSchema(ETLRecordSchema):
    """UniProt Isoform validation schema for Silver layer.

    Represents alternative protein isoforms from alternative splicing.
    """

    # === Foreign Key ===
    accession: Series[str] = pa.Field(
        nullable=False, description="FK → Protein (parent accession)"
    )

    # === Primary Key ===
    isoform_id: Series[str] = pa.Field(
        nullable=False, description="Isoform accession (e.g., P12345-2)"
    )

    # === Isoform Details ===
    isoform_name: Series[str] | None = pa.Field(
        nullable=True, description="Isoform name"
    )
    sequence_status: Series[str] | None = pa.Field(
        nullable=True, isin=SEQUENCE_STATUSES, description="Sequence display status"
    )
    sequence: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^[ACDEFGHIKLMNPQRSTVWY]+$",
        description="Isoform amino acid sequence",
    )
    sequence_length: Series[int] | None = pa.Field(
        nullable=True, ge=1, description="Isoform sequence length"
    )
    note: Series[str] | None = pa.Field(
        nullable=True, description="Isoform description/note"
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
        name = "IsoformSchema"
        description = "UniProt Isoform Silver layer validation"
