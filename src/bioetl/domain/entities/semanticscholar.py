"""Semantic Scholar domain entities.

Contains:
- SemanticScholarPublicationEntity: Domain entity (dataclass) with lineage fields

Terminology:
- Uses "Publication" for scholarly works from Semantic Scholar
- Semantic Scholar API term "Paper" is mapped to "Publication" for Ubiquitous Language

Used for DOI resolution and publication metadata enrichment via Semantic Scholar API.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class SemanticScholarPublicationEntity(BaseEntity):
    """Represents a scholarly publication from Semantic Scholar.

    Domain entity with lineage fields (run_id, content_hash, etc.).

    Terminology:
    - Uses "Publication" instead of Semantic Scholar API term "Paper"
    - Business analysts can understand the model without knowing API specifics

    Attributes:
        paper_id: Semantic Scholar Paper ID (40-char hex S2 ID).
        doi: Digital Object Identifier (normalized).
        pmid: PubMed ID.
        pmcid: PubMed Central ID.
        arxiv_id: ArXiv ID.
        corpus_id: Semantic Scholar Corpus ID.
        title: Publication title.
        abstract: Publication abstract.
        tldr: AI-generated summary (TL;DR).
        authors: JSON string of author display names (hashed for PII).
        journal: Journal name.
        volume: Journal volume.
        pages: Page numbers.
        venue: Venue name (conference/journal).
        year: Publication year.
        publication_date: Publication date (YYYY-MM-DD).
        citation_count: Number of citations.
        reference_count: Number of references.
        is_oa: Whether the work is Open Access.
        open_access_url: URL to open access PDF.
        oa_status: OA status (gold, green, hybrid, bronze, closed).
        fields_of_study: JSON string of fields of study.
        publication_types: JSON string of publication types.
        _lookup_method: How record was resolved (doi, title_fallback, title_only).
        _original_doi: Original DOI from input (for fallback records).
        source: Data source identifier (default: "semanticscholar").

    See: https://api.semanticscholar.org/api-docs/
    """

    # Primary identifier (Semantic Scholar Paper ID)
    paper_id: str

    # External identifiers (may be None)
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    arxiv_id: str | None = None
    corpus_id: int | None = None

    # Core metadata
    title: str | None = None
    abstract: str | None = None
    tldr: str | None = None

    # Authors (JSON string of hashed names)
    authors: str | None = None

    # Journal information
    journal: str | None = None
    volume: str | None = None
    pages: str | None = None
    venue: str | None = None

    # Dates
    year: int | None = None
    publication_date: str | None = None

    # Citation metrics
    citation_count: int | None = None
    reference_count: int | None = None

    # Open Access status
    is_oa: bool | None = None
    open_access_url: str | None = None
    oa_status: str | None = None

    # Classification (JSON strings)
    fields_of_study: str | None = None
    publication_types: str | None = None

    # Lookup metadata (from adapter)
    _lookup_method: str = "unknown"
    _original_doi: str | None = None

    # Source tracking
    source: str = "semanticscholar"

    def __post_init__(self) -> None:
        """Post-initialization validation."""
        super().__post_init__()
        if not self.paper_id:
            raise ValueError("Semantic Scholar Paper ID is required")


__all__ = [
    "SemanticScholarPublicationEntity",
]
