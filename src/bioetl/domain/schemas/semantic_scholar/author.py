"""Pandera schema for Semantic Scholar Author entity.

Aligned with RULES.md v5.0 and Semantic Scholar Graph API.
Source: https://api.semanticscholar.org/api-docs/graph

Author represents researcher profiles with publication metrics
and affiliations.
"""
from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class AuthorSchema(ETLRecordSchema):
    """Semantic Scholar Author validation schema for Silver layer.

    Represents a researcher profile with metrics such as h-index,
    citation count, and publication count.

    Primary Key: author_id (numeric string)
    """

    # === Primary Key ===
    author_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^\d+$",
        description="Semantic Scholar Author ID (numeric string, PK)",
    )

    # === Core Fields ===
    name: Series[str] = pa.Field(
        nullable=False,
        str_length={"min_value": 1},
        description="Display name (required)",
    )

    # === Alternative Names ===
    aliases: Series[str] | None = pa.Field(
        nullable=True,
        description="Alternative names (semicolon-separated)",
    )

    # === External Identifiers ===
    orcid: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$",
        description="ORCID identifier",
    )
    dblp_id: Series[str] | None = pa.Field(
        nullable=True,
        description="DBLP author ID",
    )

    # === Profile Information ===
    url: Series[str] | None = pa.Field(
        nullable=True,
        description="Semantic Scholar profile URL",
    )
    homepage: Series[str] | None = pa.Field(
        nullable=True,
        description="Personal homepage URL",
    )
    affiliations: Series[str] | None = pa.Field(
        nullable=True,
        description="Current affiliations (semicolon-separated)",
    )

    # === Metrics ===
    paper_count: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Number of publications",
    )
    citation_count: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Total citation count",
    )
    h_index: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="h-index",
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Silver layer allows schema drift
        ordered = True
        coerce = True
        name = "SemanticScholarAuthorSchema"
        description = "Semantic Scholar Author Silver layer validation"
