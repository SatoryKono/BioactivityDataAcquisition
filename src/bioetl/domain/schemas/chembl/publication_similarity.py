"""Pandera schema for ChEMBL Publication Similarity entity.

Aligned with RULES.md v5.24 and ChEMBL 34 schema.
Renamed from DocumentSimilaritySchema per ADR-024 (Entity Naming Unification).
"""

from __future__ import annotations

from typing import cast

import pandera.pandas as pa
from pandera.typing import DataFrame, Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.chembl.similarity_pair import valid_similarity_pair

__all__ = [
    "PublicationSimilaritySchema",
]


class PublicationSimilaritySchema(ETLRecordSchema):
    """Publication Similarity validation schema for Silver layer."""

    @pa.dataframe_check
    @classmethod
    def complete_document_pair(cls, frame: DataFrame) -> Series[bool]:
        """Require a complete public pair or a complete legacy internal pair."""
        return cast(
            Series[bool],
            frame.apply(lambda row: valid_similarity_pair(row.to_dict()), axis=1),
        )

    # === Primary Key ===
    sim_id: Series[int] = pa.Field(
        nullable=False, unique=True, description="Primary key."
    )

    # === Foreign Keys ===
    doc_1: Series[pa.Int64] | None = pa.Field(
        nullable=True,
        description="Legacy internal document 1 ID, never inferred from CHEMBL ID.",
    )
    doc_2: Series[pa.Int64] | None = pa.Field(
        nullable=True,
        description="Legacy internal document 2 ID, never inferred from CHEMBL ID.",
    )
    publication_id1: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CHEMBL[1-9]\d*$",
        description="Public ChEMBL identifier of the first document; not its internal database ID.",
    )
    publication_id2: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CHEMBL[1-9]\d*$",
        description="Public ChEMBL identifier of the second document; not its internal database ID.",
    )

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

    class Config:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
