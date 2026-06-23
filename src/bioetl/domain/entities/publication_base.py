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
        affiliation_list: JSON-serialized list of unique affiliations (unified field name).
        journal: Journal/venue name.
        issn: Primary International Standard Serial Number.
        issn_list: Canonical JSON array of ISSN values.
        publisher: Publisher name.
        page_first: First page number (unified field name).
        page_last: Last page number (unified field name).
        publication_year: Publication year (unified field name).
        publication_date: Publication date (ISO format: YYYY-MM-DD).
        citations_received: Number of citations TO this publication (unified field name).
        citations_made: Number of references FROM this publication (unified field name).
        publication_type: Canonical publication type used by Silver/Gold contracts.
        publication_type_raw: Raw provider type string retained for forensic/debug.
        publication_type_unified: Unified type Level 3 (e.g. "Journal Article").
        publication_subclass: Unified type Level 2 (e.g. "Original Experimental Data").
        publication_class: Unified type Level 1 ("EXP", "REV", or "PEER").
        language: Publication language code.
        is_oa: Whether the publication is Open Access.
        oa_status: OA status (gold, green, hybrid, bronze, closed).
        _lookup_method: How record was resolved (direct, doi, pmid, title_fallback, unknown).
        _original_id: Original identifier from input (for fallback records).
        _dq_warn: Record has data quality warnings (inherited from BaseEntity).
        _dq_error: Record has data quality errors (inherited from BaseEntity).

    Note:
        - _source field is set by transformer via entity_to_silver_record() mapping
        - Subclasses MUST define their own primary identifier field (doi, openalex_id, paper_id, pmid)
        - Subclasses MUST override _validate_invariants() to validate the primary key
    """

    # Identifiers (all nullable - subclasses define their required primary key)
    doi: str | None = None
    pmid: str | None = None
    pmc_id: str | None = None  # PubMed Central ID (with PMC prefix)
    # Canonical aliases (used in unified schemas)
    publication_doi: str | None = None
    publication_pmid: str | None = None
    publication_pmc_id: str | None = None

    # Core metadata
    title: str | None = None
    abstract: str | None = None
    authors: str | None = None  # JSON-serialized list, PII hashed
    affiliation_list: str | None = (
        None  # JSON-serialized list of unique affiliations (unified field name)
    )
    author_orcids: str | None = None  # JSON array of ORCID identifiers
    author_keys: str | None = None  # Pipe-delimited Surname_F short keys

    # Journal information
    journal: str | None = None
    issn: str | None = None
    issn_list: str | None = None
    publisher: str | None = None

    # Pagination (unified field names)
    page_first: str | None = None
    page_last: str | None = None

    # Dates
    publication_year: int | None = None
    publication_date: str | None = None  # ISO format: YYYY-MM-DD

    # Metrics (unified field names)
    citations_received: int | None = None  # Number of citations TO this publication
    citations_made: int | None = None  # Number of references FROM this publication

    # Classification
    publication_type: str | None = None  # Canonical publication type enum
    publication_type_raw: str | None = None  # Raw provider type (forensic/debug)
    publication_type_unified: str | None = None  # Level 3: "Journal Article", etc.
    publication_subclass: str | None = (
        None  # Level 2: "Original Experimental Data", etc.
    )
    publication_class: str | None = None  # Level 1: "EXP" | "REV" | "PEER"
    language: str | None = None

    # Open Access status
    is_oa: bool | None = None
    oa_status: str | None = None

    # Lookup metadata (tracks resolution strategy)
    _lookup_method: str = "unknown"  # direct | doi | pmid | title_fallback | unknown
    _original_id: str | None = None

    # Note: _dq_warn and _dq_error are inherited from BaseEntity

    # Data source identifier (system metadata field)
    _source: str = ""

    def _validate_invariants(self) -> None:
        """Publication entities share the BaseEntity invariant hook chain."""
        super()._validate_invariants()


__all__ = ["PublicationEntityBase"]
