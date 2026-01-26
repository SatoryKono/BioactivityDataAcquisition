# src/bioetl/domain/schemas/semanticscholar/publication.py
"""Pandera schema for Semantic Scholar Publication entity.

Aligned with RULES.md v5.10 and Publication Schema Unification spec.
Includes lookup metadata fields for DOI/title resolution tracking.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import (
    LOOKUP_METHODS,
    OA_STATUS_VALUES,
    PublicationBaseSchema,
)
from bioetl.domain.validation import DOI_REGEX_PATTERN

# Re-export for backwards compatibility
__all__ = [
    "DOI_REGEX_PATTERN",
    "LOOKUP_METHODS",
    "OA_STATUS_VALUES",
    "SemanticScholarPublicationSchema",
]


class SemanticScholarPublicationSchema(PublicationBaseSchema):
    """Semantic Scholar Publication validation schema for Silver layer.

    Validates publication records from Semantic Scholar Academic Graph API.
    Inherits common fields from PublicationBaseSchema:
    - Cross-references: pmid, doi, pmc_id
    - Core content: title, abstract, authors
    - Metadata: journal, year, publication_date, doc_type, language
    - Metrics: citation_count
    - Open Access: is_oa
    - Lookup tracking: lookup_method (overridden), original_id, source (overridden)
    """

    # === Primary Key (SemanticScholar-specific) ===
    paper_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^[a-f0-9]{40}$",
        description="Semantic Scholar Paper ID (40-char hex)",
    )

    # === Override lookup_method to be non-nullable ===
    lookup_method: Series[str] = pa.Field(
        alias="_lookup_method",
        nullable=False,
        isin=LOOKUP_METHODS,
        description="How record was resolved: doi, title_fallback, title_only",
    )

    # === Override _source to be non-nullable with fixed value ===
    _source: Series[str] = pa.Field(
        nullable=False,
        eq="semanticscholar",
        description="Data source identifier",
    )

    # === Provider-specific Identifiers ===
    arxiv_id: Series[str] = pa.Field(
        nullable=True,
        description="ArXiv ID",
    )

    dblp_id: Series[str] = pa.Field(
        nullable=True,
        description="DBLP publication key",
    )

    corpus_id: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=0,
        description="S2 Corpus ID",
    )

    # === Provider-specific Content ===
    tldr: Series[str] = pa.Field(
        nullable=True,
        description="AI-generated summary (TLDR)",
    )

    # === Provider-specific Journal/Venue Fields ===
    volume: Series[str] = pa.Field(
        nullable=True,
        description="Volume",
    )
    pages: Series[str] = pa.Field(
        nullable=True,
        description="Page range (legacy format, e.g., '123-456')",
    )

    first_page: Series[str] = pa.Field(
        nullable=True,
        description="First page number (parsed from pages)",
    )

    last_page: Series[str] = pa.Field(
        nullable=True,
        description="Last page number (parsed from pages)",
    )

    venue: Series[str] = pa.Field(
        nullable=True,
        description="Publication venue",
    )

    # === Provider-specific Metrics ===
    reference_count: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of references",
    )

    influential_citation_count: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of influential citations",
    )

    # === Provider-specific Open Access ===
    open_access_url: Series[str] = pa.Field(
        nullable=True,
        description="Direct link to OA PDF",
    )

    oa_status: Series[str] = pa.Field(
        nullable=True,
        isin=OA_STATUS_VALUES,
        description="Open Access status (normalized to lowercase).",
    )

    # === Provider-specific Classification ===
    fields_of_study: Series[str] = pa.Field(
        nullable=True,
        description="Fields of study (JSON array)",
    )

    publication_types: Series[str] = pa.Field(
        nullable=True,
        description="Publication types (JSON array)",
    )

    # === Author Affiliations ===
    affiliations: Series[str] = pa.Field(
        nullable=True,
        description="Author affiliations (JSON array)",
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Allow missing columns and extra columns
        coerce = True  # Coerce data types to match schema
        name = "SemanticScholarPublicationSchema"
        description = "Semantic Scholar Publication Silver layer validation"
