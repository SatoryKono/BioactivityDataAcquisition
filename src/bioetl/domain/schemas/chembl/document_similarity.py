"""Pandera schema for ChEMBL Document Similarity entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
See: https://www.ebi.ac.uk/chembl/api/data/document_similarity

Note: Pair is normalized so document_1_chembl_id < document_2_chembl_id
lexicographically for determinism (stores only upper triangle of matrix).
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class DocumentSimilaritySchema(ETLRecordSchema):
    """Document Similarity validation schema for Silver layer.

    Pairwise similarity matrix for documents. Used for recommendations
    and publication clustering.
    """

    # === Composite Primary Key ===
    document_1_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="ChEMBL ID for document 1 (PK part 1, lexicographically smaller).",
    )
    document_2_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="ChEMBL ID for document 2 (PK part 2, lexicographically larger).",
    )

    # === Similarity Metrics (Tanimoto coefficients) ===
    mol_tani: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        le=1,
        description="Tanimoto similarity coefficient (molecules) in [0, 1].",
    )
    tid_tani: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        le=1,
        description="Tanimoto similarity coefficient (targets) in [0, 1].",
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
