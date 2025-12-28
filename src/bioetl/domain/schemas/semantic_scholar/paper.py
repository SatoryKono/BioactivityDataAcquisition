"""Pandera schema for Semantic Scholar Paper entity.

Aligned with RULES.md v5.0 and Semantic Scholar Graph API.
Source: https://api.semanticscholar.org/api-docs/graph

Paper is the core entity representing scientific publications with
ML-enriched metadata including citations, embeddings, and TLDR summaries.
"""
from __future__ import annotations

from datetime import date

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

# === Fixed Value Constants ===
PUBLICATION_VENUE_TYPES = ["journal", "conference", "repository", "book", "unknown"]
PUBLICATION_TYPES = ["Review", "JournalArticle", "Conference", "Book", "Dataset", "Patent"]


class PaperSchema(ETLRecordSchema):
    """Semantic Scholar Paper validation schema for Silver layer.

    Represents a scientific publication with citation graph metadata,
    SPECTER embeddings, and AI-generated summaries (TLDR).

    Primary Key: paper_id (40-character hex string)
    Alternative Keys: corpus_id, doi, arxiv_id, pmid
    """

    # === Primary Key ===
    paper_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^[0-9a-f]{40}$",
        description="Semantic Scholar Paper ID (40-char hex, PK)",
    )

    # === Alternative Identifiers ===
    corpus_id: Series[int] | None = pa.Field(
        nullable=True,
        ge=1,
        description="Semantic Scholar Corpus ID (integer)",
    )
    doi: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^10\.\d{4,}/.+$",
        description="DOI (lowercase, without prefix)",
    )
    arxiv_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}\.\d{4,5}(v\d+)?$",
        description="arXiv ID (e.g., '2103.14030')",
    )
    pmid: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^\d+$",
        description="PubMed ID",
    )
    pmcid: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^PMC\d+$",
        description="PubMed Central ID",
    )
    mag_id: Series[str] | None = pa.Field(
        nullable=True,
        description="Microsoft Academic Graph ID (legacy)",
    )
    acl_id: Series[str] | None = pa.Field(
        nullable=True,
        description="ACL Anthology ID",
    )
    dblp_id: Series[str] | None = pa.Field(
        nullable=True,
        description="DBLP ID",
    )

    # === Core Bibliographic Fields ===
    title: Series[str] = pa.Field(
        nullable=False,
        str_length={"min_value": 1},
        description="Paper title (required)",
    )
    url: Series[str] | None = pa.Field(
        nullable=True,
        description="Semantic Scholar paper URL",
    )
    year: Series[int] | None = pa.Field(
        nullable=True,
        ge=1800,
        le=2030,
        description="Publication year",
    )
    publication_date: Series[date] | None = pa.Field(
        nullable=True,
        description="Exact publication date (YYYY-MM-DD)",
    )

    # === Venue Information ===
    venue: Series[str] | None = pa.Field(
        nullable=True,
        description="Short venue name (conference/journal)",
    )
    publication_venue_id: Series[str] | None = pa.Field(
        nullable=True,
        description="Semantic Scholar venue ID",
    )
    publication_venue_name: Series[str] | None = pa.Field(
        nullable=True,
        description="Full venue name",
    )
    publication_venue_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=PUBLICATION_VENUE_TYPES,
        description="Venue type: journal, conference, repository, book, unknown",
    )
    publication_venue_issn: Series[str] | None = pa.Field(
        nullable=True,
        description="Venue ISSN",
    )
    publication_venue_url: Series[str] | None = pa.Field(
        nullable=True,
        description="Venue URL",
    )

    # === Journal-specific Fields ===
    journal_name: Series[str] | None = pa.Field(
        nullable=True,
        description="Journal name (if venue is journal)",
    )
    journal_volume: Series[str] | None = pa.Field(
        nullable=True,
        description="Journal volume",
    )
    journal_pages: Series[str] | None = pa.Field(
        nullable=True,
        description="Page numbers",
    )

    # === Content Fields ===
    abstract: Series[str] | None = pa.Field(
        nullable=True,
        description="Abstract text (may contain LaTeX)",
    )
    tldr: Series[str] | None = pa.Field(
        nullable=True,
        description="AI-generated summary (TLDR model output)",
    )

    # === Citation Metrics ===
    citation_count: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Total citation count",
    )
    influential_citation_count: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Highly influential citation count",
    )
    reference_count: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Number of references in bibliography",
    )

    # === Open Access ===
    is_open_access: Series[bool] | None = pa.Field(
        nullable=True,
        description="Whether paper is open access",
    )
    open_access_pdf_url: Series[str] | None = pa.Field(
        nullable=True,
        description="URL to open access PDF",
    )

    # === Classification Fields ===
    fields_of_study: Series[str] | None = pa.Field(
        nullable=True,
        description="Research fields (semicolon-separated)",
    )
    s2_fields_of_study: Series[str] | None = pa.Field(
        nullable=True,
        description="S2 classification as 'field:score; field:score'",
    )
    publication_types: Series[str] | None = pa.Field(
        nullable=True,
        description="Publication types (semicolon-separated)",
    )

    # === Embedding Fields ===
    embedding_model: Series[str] | None = pa.Field(
        nullable=True,
        description="Embedding model name (specter_v1, specter2, etc.)",
    )
    embedding_vector: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON-encoded embedding vector (768-dim float array)",
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Silver layer allows schema drift
        ordered = True
        coerce = True
        name = "SemanticScholarPaperSchema"
        description = "Semantic Scholar Paper Silver layer validation"
