"""Semantic Scholar domain entities.

Contains:
- SemanticScholarPublicationEntity: Domain entity (dataclass) with lineage fields

Terminology:
- Uses "Publication" for scholarly works from Semantic Scholar
- Semantic Scholar API term "Paper" is mapped to "Publication" for Ubiquitous Language

Used for DOI resolution and publication metadata enrichment via Semantic Scholar API.

Note: SemanticScholarPublicationEntity inherits common fields from PublicationEntityBase.
Provider-specific fields (paper_id, pmc_id, arxiv_id, etc.) are defined here.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.publication_base import PublicationEntityBase


@dataclass(frozen=True, kw_only=True)
class SemanticScholarPublicationEntity(PublicationEntityBase):
    """Represents a scholarly publication from Semantic Scholar.

    Domain entity with lineage fields (run_id, content_hash, etc.).
    Inherits common publication fields from PublicationEntityBase.

    Terminology:
    - Uses "Publication" instead of Semantic Scholar API term "Paper"
    - Business analysts can understand the model without knowing API specifics

    Inherited from PublicationEntityBase:
        doi, pmid, title, abstract, authors, journal, issn, publisher,
        year, publication_date, citation_count, doc_type, language, is_oa,
        oa_status, _lookup_method, _original_id, source.

    SemanticScholar-specific Attributes:
        paper_id: Semantic Scholar Paper ID (40-char hex S2 ID). REQUIRED.
        pmc_id: PubMed Central ID (format: PMC1234567).
        arxiv_id: ArXiv ID.
        corpus_id: Semantic Scholar Corpus ID.
        tldr: AI-generated summary (TL;DR).
        volume: Journal volume.
        pages: Page numbers.
        venue: Venue name (conference/journal).
        reference_count: Number of references.
        open_access_url: URL to open access PDF.
        fields_of_study: JSON string of fields of study.
        publication_types: JSON string of publication types.

    Note: paper_id is required for Semantic Scholar publications.

    See: https://api.semanticscholar.org/api-docs/
    """

    # Primary identifier (Semantic Scholar Paper ID) - REQUIRED
    paper_id: str

    # SemanticScholar-specific external identifiers
    # pmc_id: PubMed Central ID (format: "PMC1234567")
    pmc_id: str | None = None
    arxiv_id: str | None = None
    corpus_id: int | None = None

    # SemanticScholar-specific: AI-generated summary
    tldr: str | None = None

    # SemanticScholar-specific journal/venue information
    volume: str | None = None
    pages: str | None = None
    venue: str | None = None

    # SemanticScholar-specific metrics
    reference_count: int | None = None

    # SemanticScholar-specific OA URL
    open_access_url: str | None = None

    # SemanticScholar-specific classification (JSON strings)
    fields_of_study: str | None = None
    publication_types: str | None = None

    # Override: Default source for SemanticScholar
    source: str = "semanticscholar"

    def __post_init__(self) -> None:
        """Post-initialization validation.

        Validates that paper_id is provided (required for Semantic Scholar publications).
        """
        super().__post_init__()
        if not self.paper_id:
            raise ValueError("Semantic Scholar Paper ID is required")


__all__ = [
    "SemanticScholarPublicationEntity",
]
