"""Pandera schema for ChEMBL Publication Similarity entity.

Aligned with RULES.md v5.24 and ChEMBL 34 schema.
Renamed from DocumentSimilaritySchema per ADR-024 (Entity Naming Unification).
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

__all__ = [
    "PublicationSimilaritySchema",
]


class PublicationSimilaritySchema(ETLRecordSchema):
    """Publication Similarity validation schema for Silver layer."""

    # === Primary Key ===
    sim_id: Series[int] = pa.Field(nullable=False, description="Primary key.")

    # === Foreign Keys ===
    doc_1: Series[int] = pa.Field(nullable=False, description="FK to document 1.")
    doc_2: Series[int] = pa.Field(nullable=False, description="FK to document 2.")

    # === Identifiers ===
    pubmed_id1: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^\d+$",
        description="PubMed identifier 1 (numeric string).",
    )
    pubmed_id2: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^\d+$",
        description="PubMed identifier 2 (numeric string).",
    )

    # === Metrics ===
    tid_tani: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        le=1,
        description="Tanimoto coefficient (TID).",
    )
    mol_tani: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        le=1,
        description="Tanimoto coefficient (MOL).",
    )
    avg_tani: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        le=1,
        description="Average Tanimoto coefficient.",
    )
    max_tani: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        le=1,
        description="Max Tanimoto coefficient.",
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
