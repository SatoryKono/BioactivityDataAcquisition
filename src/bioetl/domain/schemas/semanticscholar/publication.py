# src/bioetl/domain/schemas/semanticscholar/publication.py
"""Pandera schema for Semantic Scholar Publication entity.

Aligned with RULES.md v5.10.
Includes lookup metadata fields for DOI/title resolution tracking.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import (
    LOOKUP_METHODS,
    PublicationBaseSchema,
)
from bioetl.domain.validation import DOI_REGEX_PATTERN

# Re-export for backwards compatibility
__all__ = ["DOI_REGEX_PATTERN", "LOOKUP_METHODS", "OA_STATUS_VALUES", "SemanticScholarPublicationSchema"]

# Open Access status values (normalized to lowercase for consistency with OpenAlex)
OA_STATUS_VALUES = ["gold", "green", "hybrid", "bronze", "closed"]


class SemanticScholarPublicationSchema(PublicationBaseSchema):
    """Semantic Scholar Publication validation schema for Silver layer.

    Validates publication records from Semantic Scholar Academic Graph API.
    Includes lookup metadata for tracking DOI vs title resolution.
    """

    # === Lookup metadata (SemanticScholar-specific) ===
    lookup_method: Series[str] = pa.Field(
        alias="_lookup_method",
        nullable=False,
        isin=LOOKUP_METHODS,
        description="How record was resolved: doi, title_fallback, title_only",
    )
    original_id: Series[str] = pa.Field(
        alias="_original_id",
        nullable=True,
        description="Original identifier from input (for fallback records)",
    )

    # === Primary Key ===
    paper_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^[a-f0-9]{40}$",
        description="Semantic Scholar Paper ID (40-char hex)",
    )

    # === Provider-specific Identifiers ===
    arxiv_id: Series[str] = pa.Field(
        nullable=True,
        description="ArXiv ID",
    )

    corpus_id: Series[int] = pa.Field(
        nullable=True,
        ge=0,
        description="S2 Corpus ID",
    )

    # === Provider-specific Content ===
    tldr: Series[str] = pa.Field(
        nullable=True,
        description="AI-generated summary (TLDR)",
    )
    authors: Series[str] = pa.Field(
        nullable=True,
        description="JSON array of author names",
    )

    # === Publication metadata ===
    publication_date: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{2}-\d{2}$",
        description="Publication date (YYYY-MM-DD)",
    )
    doc_type: Series[str] = pa.Field(
        nullable=True,
        description="Publication type",
    )

    # === Journal/Venue (provider-specific) ===
    journal: Series[str] = pa.Field(
        nullable=True,
        description="Journal name",
    )
    volume: Series[str] = pa.Field(
        nullable=True,
        description="Volume",
    )
    pages: Series[str] = pa.Field(
        nullable=True,
        description="Page range",
    )

    venue: Series[str] = pa.Field(
        nullable=True,
        description="Publication venue",
    )

    # === Metrics ===
    citation_count: Series[int] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of citations",
    )
    reference_count: Series[int] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of references",
    )

    # === Open Access ===
    is_oa: Series[bool] = pa.Field(
        nullable=True,
        description="Is Open Access",
    )

    open_access_url: Series[str] = pa.Field(
        nullable=True,
        description="Direct link to OA PDF",
    )

    oa_status: Series[str] = pa.Field(
        nullable=True,
        isin=OA_STATUS_VALUES,
        description="Open Access status (normalized to lowercase).",
    )

    # === Classification ===
    fields_of_study: Series[str] = pa.Field(
        nullable=True,
        description="Fields of study (JSON array)",
    )

    publication_types: Series[str] = pa.Field(
        nullable=True,
        description="Publication types (JSON array)",
    )

    # === Source Tracking ===
    source: Series[str] = pa.Field(
        nullable=False,
        eq="semanticscholar",
        description="Data source identifier",
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Allow missing columns and extra columns
        coerce = True  # Coerce data types to match schema
        name = "SemanticScholarPublicationSchema"
        description = "Semantic Scholar Publication Silver layer validation"
