"""Pandera schema for Semantic Scholar Paper-Author junction.

Aligned with RULES.md v5.0 and Semantic Scholar Graph API.
Source: https://api.semanticscholar.org/api-docs/graph

PaperAuthor is a junction table representing the M:N relationship
between Papers and Authors, including author position.
"""
from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class PaperAuthorSchema(ETLRecordSchema):
    """Semantic Scholar Paper-Author junction validation schema.

    Represents the relationship between a paper and its authors,
    including the author's position in the author list.

    Composite Primary Key: (paper_id, author_id, author_position)
    """

    # === Foreign Keys ===
    paper_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^[0-9a-f]{40}$",
        description="FK to SemanticScholarPaper",
    )
    author_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^\d+$",
        description="FK to SemanticScholarAuthor",
    )

    # === Position ===
    author_position: Series[int] = pa.Field(
        nullable=False,
        ge=0,
        description="Position in author list (0-based index)",
    )

    # === Denormalized Fields ===
    author_name: Series[str] | None = pa.Field(
        nullable=True,
        description="Author name as appears in the paper",
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Silver layer allows schema drift
        ordered = True
        coerce = True
        name = "SemanticScholarPaperAuthorSchema"
        description = "Semantic Scholar Paper-Author junction Silver layer validation"
