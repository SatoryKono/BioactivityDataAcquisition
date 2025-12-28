"""Pandera schema for Semantic Scholar Citation entity.

Aligned with RULES.md v5.0 and Semantic Scholar Graph API.
Source: https://api.semanticscholar.org/api-docs/graph

Citation represents directed edges in the citation graph between papers,
including influence indicators and citation contexts.
"""
from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

# === Fixed Value Constants ===
CITATION_INTENTS = ["methodology", "background", "result"]


class CitationSchema(ETLRecordSchema):
    """Semantic Scholar Citation validation schema for Silver layer.

    Represents a directed citation edge from citing_paper to cited_paper,
    with optional influence indicators and citation contexts.

    Composite Primary Key: (citing_paper_id, cited_paper_id)

    Note:
        - citations endpoint: returns papers that cite the given paper
        - references endpoint: returns papers cited by the given paper
    """

    # === Primary Key (Composite) ===
    citing_paper_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^[0-9a-f]{40}$",
        description="ID of the citing paper (FK to Paper)",
    )
    cited_paper_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^[0-9a-f]{40}$",
        description="ID of the cited paper (FK to Paper)",
    )

    # === Citation Metadata ===
    is_influential: Series[bool] | None = pa.Field(
        nullable=True,
        description="Whether this is a highly influential citation",
    )

    # === Citation Context ===
    contexts: Series[str] | None = pa.Field(
        nullable=True,
        description="Citation context sentences (triple-pipe separated: ' ||| ')",
    )
    intents: Series[str] | None = pa.Field(
        nullable=True,
        description="Citation intents (semicolon-separated): methodology, background, result",
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Silver layer allows schema drift
        ordered = True
        coerce = True
        name = "SemanticScholarCitationSchema"
        description = "Semantic Scholar Citation Silver layer validation"

