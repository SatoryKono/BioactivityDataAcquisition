"""Semantic Scholar domain entities.

Contains entities for Semantic Scholar data: SemanticScholarPaper.
Maps to Publication layer with citation graph enrichment.

API Reference: https://api.semanticscholar.org/api-docs/graph
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.domain.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class SemanticScholarPaper(BaseEntity):
    """Represents a paper from Semantic Scholar API.

    Contains paper metadata with ML-enriched fields like embeddings,
    influential citations, and fields of study classification.

    Field Mapping from S2 API:
    - paperId -> semantic_scholar_id (primary)
    - externalIds.DOI -> doi (fallback identifier)
    - externalIds.PubMed -> pmid (cross-reference)
    - title -> title
    - authors[].name -> authors (list[str])
    - venue -> journal
    - year -> year
    - abstract -> abstract
    - citationCount -> citation_count
    - influentialCitationCount -> influential_citation_count
    - embedding.vector -> _embedding (excluded from hash)
    - fieldsOfStudy -> fields_of_study

    Attributes:
        semantic_scholar_id: Primary S2 paper identifier (paperId).
        doi: DOI if available (lowercased).
        pmid: PubMed ID if available.
        title: Paper title.
        authors: List of author names.
        journal: Venue/journal name.
        year: Publication year.
        abstract: Paper abstract.
        citation_count: Total citation count.
        influential_citation_count: Count of influential citations.
        fields_of_study: ML-classified research fields.
        _embedding: SPECTER embedding vector (excluded from content hash).

    """

    # Primary identifier
    semantic_scholar_id: str

    # Cross-reference identifiers
    doi: str | None = None
    pmid: int | None = None

    # Bibliographic metadata
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    journal: str | None = None
    year: int | None = None
    abstract: str | None = None

    # Citation metrics
    citation_count: int | None = None
    influential_citation_count: int | None = None

    # ML-enriched fields
    fields_of_study: list[str] = field(default_factory=list)

    # Embedding vector (excluded from content hash, stored in Silver only)
    _embedding: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Post-initialization validation."""
        super().__post_init__()
        if not self.semantic_scholar_id:
            raise ValueError("Semantic Scholar paper ID is required")
