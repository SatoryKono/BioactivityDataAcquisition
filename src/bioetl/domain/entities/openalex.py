"""OpenAlex domain entities.

Contains:
- OpenAlexPublicationRecord: DTO (Pydantic) for type-safe data transfer at boundaries
- OpenAlexPublicationEntity: Domain entity (dataclass) with lineage fields

DTO Design:
- Uses extra='forbid' to detect API changes early
- frozen=True ensures immutability
- Adapters return DTOs, transformers convert to Domain Entities

Terminology:
- Uses "Publication" for scholarly works from OpenAlex
- OpenAlex API term "Work" is mapped to "Publication" for Ubiquitous Language

Used for batch DOI resolution and publication metadata enrichment.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField

from bioetl.domain.entities.base import BaseEntity

# Document type mapping from OpenAlex types to internal types
OPENALEX_TYPE_MAP = {
    "article": "PUBLICATION",
    "journal-article": "PUBLICATION",
    "book-chapter": "PUBLICATION",
    "book": "PUBLICATION",
    "dissertation": "PUBLICATION",
    "dataset": "DATASET",
    "preprint": "PREPRINT",
    "posted-content": "PREPRINT",
    "proceedings": "PUBLICATION",
    "proceedings-article": "PUBLICATION",
    "report": "PUBLICATION",
    "standard": "PUBLICATION",
    "peer-review": "PUBLICATION",
    "editorial": "PUBLICATION",
    "erratum": "PUBLICATION",
    "letter": "PUBLICATION",
    "review": "PUBLICATION",
    "other": "OTHER",
}

# Lookup method values for tracking DOI resolution strategy
LOOKUP_METHODS = ["doi", "title_fallback", "title_only", "unknown"]


# === Pydantic DTO Model ===


class OpenAlexPublicationRecord(BaseModel):
    """Scholarly work DTO from OpenAlex.

    Represents publication metadata from OpenAlex API for DOI resolution
    and citation enrichment.

    Required field: openalex_id.

    Example:
        >>> record = OpenAlexPublicationRecord(
        ...     openalex_id="W2148763428",
        ...     doi="10.1038/nature12373",
        ...     title="Example Article",
        ...     journal="Nature",
        ...     year=2024,
        ... )
        >>> record.model_dump()
        {'openalex_id': 'W2148763428', 'doi': '10.1038/nature12373', ...}

    See: https://docs.openalex.org/api-entities/works
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED, OpenAlex Work ID)
    openalex_id: str = PydanticField(description="OpenAlex Work ID (e.g., W2148763428)")

    # DOI (may be None for some works)
    doi: str | None = PydanticField(
        default=None, description="Digital Object Identifier (normalized)"
    )

    # Core metadata
    title: str | None = PydanticField(default=None, description="Publication title")
    abstract: str | None = PydanticField(
        default=None,
        description="Publication abstract (reconstructed from inverted index)",
    )

    # Authors (JSON-serialized list of hashed names for PII compliance)
    authors: str | None = PydanticField(
        default=None, description="Author names (JSON array, hashed for PII)"
    )

    # Journal information
    journal: str | None = PydanticField(
        default=None, description="Source name (journal/venue)"
    )
    issn: str | None = PydanticField(default=None, description="ISSN-L")
    publisher: str | None = PydanticField(
        default=None, description="Host organization name"
    )

    # Dates
    year: int | None = PydanticField(default=None, description="Publication year")
    publication_date: str | None = PydanticField(
        default=None, description="Publication date (YYYY-MM-DD)"
    )

    # Document type (mapped from OpenAlex type)
    doc_type: str = PydanticField(default="PUBLICATION", description="Document type")

    # Open Access status
    is_oa: bool | None = PydanticField(default=None, description="Is Open Access")
    oa_status: str | None = PydanticField(
        default=None, description="OA status (gold, green, hybrid, bronze, closed)"
    )

    # Citation metrics
    # OpenAlex source field: cited_by_count
    # Unified BioETL field: citation_count (standardized across all providers)
    citation_count: int | None = PydanticField(
        default=None, description="Number of citations (from OpenAlex cited_by_count)"
    )

    # Concepts (top-level only)
    concepts: list[str] = PydanticField(
        default_factory=list, description="Top concept names"
    )

    # Additional metadata
    language: str | None = PydanticField(default=None, description="Language code")

    # Lookup metadata (from adapter)
    # Note: Pydantic doesn't allow underscore-prefixed fields, so these use public names
    lookup_method: str = PydanticField(
        default="unknown",
        description="How record was resolved: doi, title_fallback, title_only",
    )
    original_doi: str | None = PydanticField(
        default=None,
        description="Original DOI from input CSV (for fallback records)",
    )

    # Source tracking
    source: str = PydanticField(default="openalex", description="Data source")


# === Dataclass Domain Entity ===


@dataclass(frozen=True, kw_only=True)
class OpenAlexPublicationEntity(BaseEntity):
    """Represents a scholarly publication from OpenAlex.

    Domain entity with lineage fields (run_id, content_hash, etc.).
    For DTO without lineage, use OpenAlexPublicationRecord.

    Terminology:
    - Uses "Publication" instead of OpenAlex API term "Work" for Ubiquitous Language
    - Business analysts can understand the model without knowing OpenAlex API specifics

    Attributes:
        openalex_id: OpenAlex Work ID (e.g., W2148763428).
        doi: Digital Object Identifier (normalized: lowercase, stripped).
        title: Publication title.
        abstract: Publication abstract (reconstructed from inverted index).
        authors: JSON-serialized list of hashed author names (PII compliance).
        journal: Source name (journal/venue).
        issn: ISSN-L identifier.
        publisher: Host organization name.
        year: Publication year.
        publication_date: Publication date (YYYY-MM-DD).
        doc_type: Document type (PUBLICATION, PREPRINT, etc.).
        is_oa: Whether the work is Open Access.
        oa_status: OA status (gold, green, hybrid, bronze, closed).
        citation_count: Number of citations (from OpenAlex cited_by_count).
        concepts: Top concept names from OpenAlex.
        language: Publication language code.
        _lookup_method: How record was resolved (doi, title_fallback, title_only).
        _original_doi: Original DOI from input CSV (for fallback records).
        source: Data source identifier (default: "openalex").

    See: https://docs.openalex.org/api-entities/works
    """

    # Primary identifier (OpenAlex Work ID)
    openalex_id: str

    # DOI (may be None for some works)
    doi: str | None = None

    # Core metadata
    title: str | None = None
    abstract: str | None = None

    # Authors (JSON-serialized list of hashed names for PII compliance)
    authors: str | None = None

    # Journal information
    journal: str | None = None
    issn: str | None = None
    publisher: str | None = None

    # Dates
    year: int | None = None
    publication_date: str | None = None

    # Document type (mapped from OpenAlex type)
    doc_type: str = "PUBLICATION"

    # Open Access status
    is_oa: bool | None = None
    oa_status: str | None = None

    # Citation metrics
    # OpenAlex source field: cited_by_count
    # Unified BioETL field: citation_count (standardized across all providers)
    citation_count: int | None = None

    # Concepts (top-level only)
    concepts: list[str] = field(default_factory=list)

    # Additional metadata
    language: str | None = None

    # Lookup metadata (from adapter)
    _lookup_method: str = "unknown"
    _original_doi: str | None = None

    # Source tracking
    source: str = "openalex"

    def __post_init__(self) -> None:
        """Post-initialization validation."""
        super().__post_init__()
        if not self.openalex_id:
            raise ValueError("OpenAlex Publication ID is required")


__all__ = [
    "LOOKUP_METHODS",
    "OPENALEX_TYPE_MAP",
    "OpenAlexPublicationEntity",
    "OpenAlexPublicationRecord",
]
