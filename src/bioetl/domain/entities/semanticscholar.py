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
        dblp_id: DBLP publication key.
        corpus_id: Semantic Scholar Corpus ID.
        tldr: AI-generated summary (TL;DR).
        volume: Journal volume (parsed from combined format like "32 4").
        issue: Journal issue number (parsed from combined volume/issue).
        page_range: Page numbers.
        venue: Venue name (conference/journal).
        influential_citation_count: Number of influential citations.
        open_access_url: URL to open access PDF.
        subject_fields: JSON string of fields of study.
        publication_type: JSON string of publication types.
        author_s2_ids: JSON string of S2 author IDs (40-char hex).
        author_h_indices: JSON string of h-index values.
        citation_contexts: JSON string of citation context sentences.

    Note: paper_id is required for Semantic Scholar publications.

    See: https://api.semanticscholar.org/api-docs/
    """

    # Primary identifier (Semantic Scholar Paper ID) - REQUIRED
    paper_id: str

    # SemanticScholar-specific external identifiers (in addition to inherited pmc_id)
    arxiv_id: str | None = None
    dblp_id: str | None = None
    corpus_id: int | None = None

    # SemanticScholar-specific: AI-generated summary
    tldr: str | None = None

    # SemanticScholar-specific journal information
    volume: str | None = None
    issue: str | None = (
        None  # Parsed from combined volume/issue (e.g., "32 4" → issue=4)
    )
    page_range: str | None = None  # Legacy: "first-last" format
    # first_page and last_page inherited from PublicationEntityBase

    # SemanticScholar-specific metrics
    # Note: citations_made inherited from PublicationEntityBase
    influential_citation_count: int | None = None

    # SemanticScholar-specific OA URL
    open_access_url: str | None = None

    # SemanticScholar-specific classification (JSON strings)
    subject_fields: str | None = None
    publication_types: str | None = None  # JSON array of publication types

    # Author identifiers (for author-level analytics and disambiguation)
    author_s2_ids: str | None = None  # JSON array of S2 author IDs (40-char hex)
    author_h_indices: str | None = None  # JSON array of h-index values

    # Citation context (for citation sentiment analysis)
    citation_contexts: str | None = None  # JSON array of context sentences

    # Override: Default source for SemanticScholar
    _source: str = "semanticscholar"

    def _validate_invariants(self) -> None:
        """Validate Semantic Scholar-specific publication invariants."""
        super()._validate_invariants()
        if not self.paper_id:
            raise ValueError("Semantic Scholar Paper ID is required")


__all__ = [
    "SemanticScholarPublicationEntity",
]
