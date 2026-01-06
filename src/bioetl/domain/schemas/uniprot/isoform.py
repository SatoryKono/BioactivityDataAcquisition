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
        nullable=True, description="Sequence display status"
    )

    @pa.check("sequence_status", name="sequence_status_values")
    def _check_sequence_status(cls, series: Series[str]) -> Series[bool]:
        """Validate sequence status values."""
        return series.isna() | series.isin(SEQUENCE_STATUSES)

    sequence: Series[str] | None = pa.Field(
        nullable=True,
        description="Isoform amino acid sequence",
    )

    @pa.check("sequence", name="sequence_format")
    def _check_sequence(cls, series: Series[str]) -> Series[bool]:
        """Validate amino acid sequence."""
        return series.isna() | series.str.match(r"^[ACDEFGHIKLMNPQRSTVWY]+$")

    sequence_length: Series[int] | None = pa.Field(
        nullable=True, description="Isoform sequence length"
    )

    @pa.check("sequence_length", name="sequence_length_positive")
    def _check_sequence_length(cls, series: Series[int]) -> Series[bool]:
        """Validate sequence length is positive."""
        return series.isna() | (series >= 1)

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
