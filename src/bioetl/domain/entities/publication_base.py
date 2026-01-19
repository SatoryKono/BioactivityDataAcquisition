"""Base class for publication entities across all providers.

Provides common fields shared by CrossRef, OpenAlex, SemanticScholar, and PubMed
publication entities. Provider-specific fields are defined in subclasses.

This base class enables:
- Unified type hints for cross-provider operations
- Common validation logic
- Composite pipeline support

Subclasses:
- CrossRefPublicationEntity (CrossRef) - doi required
- OpenAlexPublicationEntity (OpenAlex) - openalex_id required
- SemanticScholarPublicationEntity (SemanticScholar) - paper_id required
- PubMedPublicationEntity (PubMed) - pmid required

Field Classification:
- REQUIRED: entity_id, content_hash (inherited from BaseEntity)
- API-OPTIONAL: All fields in this class (providers may not return all)
- LOOKUP: _lookup_method, _original_id (resolution tracking)
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class PublicationEntityBase(BaseEntity):
    """Base publication entity with common fields shared across all providers.

    Contains the intersection of fields available from CrossRef, OpenAlex,
    SemanticScholar, and PubMed APIs. Each subclass adds provider-specific
    fields and validates its own primary key.

    Attributes:
        doi: Digital Object Identifier (normalized: lowercase, stripped).
        pmid: PubMed ID for biomedical literature.
        pmc_id: PubMed Central ID (with PMC prefix).
        title: Publication title.
        abstract: Publication abstract (HTML tags stripped).
        authors: JSON-serialized list of author names (hashed for PII compliance).
        journal: Journal/venue name.
        issn: International Standard Serial Number.
        publisher: Publisher name.
        first_page: First page number (unified across providers).
        last_page: Last page number (unified across providers).
        year: Publication year.
        publication_date: Publication date (ISO format: YYYY-MM-DD).
        citation_count: Number of citations.
        doc_type: Document type (PUBLICATION, PREPRINT, etc.).
        language: Publication language code.
        is_oa: Whether the publication is Open Access.
        oa_status: OA status (gold, green, hybrid, bronze, closed).
        _lookup_method: How record was resolved (direct, doi, pmid, title_fallback, unknown).
        _original_id: Original identifier from input (for fallback records).
        _dq_warn: Record has data quality warnings (inherited from BaseEntity).
        _dq_error: Record has data quality errors (inherited from BaseEntity).
        source: Data source identifier (e.g., "crossref", "openalex").

    Note:
        Subclasses MUST:
        - Define their own primary identifier field (doi, openalex_id, paper_id, pmid)
        - Override __post_init__ to validate the primary key
        - Set appropriate default for `source` field
    """

    # Identifiers (all nullable - subclasses define their required primary key)
    doi: str | None = None
    pmid: str | None = None
    pmc_id: str | None = None  # PubMed Central ID (with PMC prefix)

    # Core metadata
    title: str | None = None
    abstract: str | None = None
    authors: str | None = None  # JSON-serialized list, PII hashed

    # Journal information
    journal: str | None = None
    issn: str | None = None
    publisher: str | None = None

    # Pagination (unified across providers)
    first_page: str | None = None
    last_page: str | None = None

    # Dates
    year: int | None = None
    publication_date: str | None = None  # ISO format: YYYY-MM-DD

    # Metrics
    citation_count: int | None = None

    # Classification
    doc_type: str = "PUBLICATION"
    language: str | None = None

    # Open Access status
    is_oa: bool | None = None
    oa_status: str | None = None

    # Lookup metadata (tracks resolution strategy)
    _lookup_method: str = "unknown"  # direct | doi | pmid | title_fallback | unknown
    _original_id: str | None = None

    # Note: _dq_warn and _dq_error are inherited from BaseEntity

    # Source tracking (subclasses should override default)
    source: str = ""

    def __post_init__(self) -> None:
        """Validate base entity constraints.

        Subclasses MUST call super().__post_init__() and then validate
        their own primary key field.
        """
        super().__post_init__()
        # Base class does not enforce primary key - subclasses do


__all__ = ["PublicationEntityBase"]
