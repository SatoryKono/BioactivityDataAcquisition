# src/bioetl/domain/schemas/semanticscholar/publication.py
"""Pandera schema for Semantic Scholar Publication entity.

Aligned with RULES.md v5.24 and Publication Schema Unification spec.
Includes lookup metadata fields for DOI/title resolution tracking.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import (
    OA_STATUS_VALUES,
    PublicationBaseSchema,
)
from bioetl.domain.validation import DOI_REGEX_PATTERN

# Re-export for backwards compatibility
__all__ = [
    "DOI_REGEX_PATTERN",
    "OA_STATUS_VALUES",
    "SemanticScholarPublicationSchema",
]


class SemanticScholarPublicationSchema(PublicationBaseSchema):
    """Semantic Scholar Publication validation schema for Silver layer.

    Validates publication records from Semantic Scholar Academic Graph API.
    Inherits common fields from PublicationBaseSchema:
    - Cross-references: pmid, doi
    - Core content: title, abstract, authors
    - Metadata: journal, year, publication_date
    - Metrics: citation_count
    - Open Access: is_oa
    - Lookup tracking: lookup_method, original_id, source (overridden)

    Fields excluded from PyArrow/Gold schemas:
    - pmc_id: Excluded per design (2026-01)
    - arxiv_id: Excluded per design (2026-01)
    - language: S2 API doesn't return language
    - doc_type: S2 uses publication_type (JSON array) instead
    """

    # === Override inherited fields to allow missing (align with excluded fields) ===
    # Note: pmc_id is already nullable in base schema, just re-declaring here for clarity
    pmc_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^PMC\d+$",
        description="PubMed Central ID",
    )

    # === Primary Key (SemanticScholar-specific) ===
    paper_id: Series[str] = pa.Field(
        nullable=False,
        unique=True,
        str_matches=r"^[a-f0-9]{40}$",
        description="Semantic Scholar Paper ID (40-char hex)",
    )
    title: Series[str] = pa.Field(
        nullable=True,
        description="Publication title when available from Semantic Scholar.",
    )

    # _lookup_method: inherited from PublicationBaseSchema (non-nullable, isin=LOOKUP_METHODS)

    # === Override _source to be non-nullable with fixed value ===
    _source: Series[str] = pa.Field(
        nullable=False,
        eq="semanticscholar",
        description="Data source identifier",
    )

    # === Provider-specific Identifiers ===
    # Note: arxiv_id excluded per design (2026-01)

    dblp_id: Series[str] = pa.Field(
        nullable=True,
        description="DBLP publication key",
    )

    corpus_id: Series[pd.Int64Dtype] | None = pa.Field(
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
    page_range: Series[str] = pa.Field(
        nullable=True,
        description="Page range (legacy format, e.g., '123-456')",
    )

    # === Provider-specific Metrics ===

    influential_citation_count: Series[pd.Int64Dtype] | None = pa.Field(
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
    subject_fields: Series[str] = pa.Field(
        nullable=True,
        description="Fields of study (JSON array)",
    )
    subject_fields_canonical_json: Series[str] = pa.Field(
        nullable=True,
        description="Canonical JSON companion for subject-fields payload.",
    )
    subject_fields_raw_json: Series[str] = pa.Field(
        nullable=True,
        description="Raw provider JSON for subject-fields payload.",
    )

    publication_type: Series[str] = pa.Field(
        nullable=True,
        description="Publication types (pipe-delimited string)",
    )

    publication_types: Series[str] = pa.Field(
        nullable=True,
        description="Publication types (JSON array)",
    )
    publication_types_canonical_json: Series[str] = pa.Field(
        nullable=True,
        description="Canonical JSON companion for publication-types payload.",
    )
    publication_types_raw_json: Series[str] = pa.Field(
        nullable=True,
        description="Raw provider JSON for publication-types payload.",
    )

    # === Author Identifiers (for author-level analytics and disambiguation) ===
    author_s2_ids: Series[str] = pa.Field(
        nullable=True,
        description="Semantic Scholar author IDs (JSON array of 40-char hex IDs)",
    )

    # author_orcids: inherited from PublicationBaseSchema

    author_h_indices: Series[str] = pa.Field(
        nullable=True,
        description="Author h-index values (JSON array, null for missing)",
    )
    author_h_indices_canonical_json: Series[str] = pa.Field(
        nullable=True,
        description="Canonical JSON companion for author h-index payload.",
    )
    author_h_indices_raw_json: Series[str] = pa.Field(
        nullable=True,
        description="Raw provider JSON for author h-index payload.",
    )

    # === Citation Context (for citation sentiment analysis) ===
    citation_contexts: Series[str] = pa.Field(
        nullable=True,
        description="Citation context sentences (JSON array)",
    )
    citation_contexts_canonical_json: Series[str] = pa.Field(
        nullable=True,
        description="Canonical JSON companion for citation-context payload.",
    )
    citation_contexts_raw_json: Series[str] = pa.Field(
        nullable=True,
        description="Raw provider JSON for citation-context payload.",
    )

    class Config:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Pandera configuration."""

        strict = False  # Allow missing columns and extra columns
        coerce = True  # Coerce data types to match schema
        name = "SemanticScholarPublicationSchema"
        description = "Semantic Scholar Publication Silver layer validation"
