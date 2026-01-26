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

Note: OpenAlexPublicationEntity inherits common fields from PublicationEntityBase.
Provider-specific fields (openalex_id, concepts) are defined here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField

from bioetl.domain.entities.publication_base import PublicationEntityBase

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

    # MeSH terms (Medical Subject Headings)
    mesh: list[str] = PydanticField(
        default_factory=list, description="MeSH descriptor names"
    )

    # Keywords
    keywords: list[str] = PydanticField(
        default_factory=list, description="Author-assigned keywords"
    )

    # External identifiers
    # pmc_id: PubMed Central ID (format: "PMC1234567")
    pmc_id: str | None = PydanticField(
        default=None, description="PubMed Central ID (format: PMC1234567)"
    )
    mag_id: str | None = PydanticField(
        default=None, description="Microsoft Academic Graph ID"
    )

    # Additional metadata
    language: str | None = PydanticField(default=None, description="Language code")

    # Bibliographic info (from biblio object)
    volume: str | None = PydanticField(
        default=None, description="Journal volume number"
    )
    issue: str | None = PydanticField(default=None, description="Journal issue number")

    # Additional metrics
    fwci: float | None = PydanticField(
        default=None, description="Field-Weighted Citation Impact"
    )
    referenced_works_count: int | None = PydanticField(
        default=None, description="Number of works referenced"
    )

    # Quality indicators
    is_retracted: bool = PydanticField(
        default=False, description="Whether the publication has been retracted"
    )

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

    # Note: _source is set by transformer via entity_to_silver_record() mapping


# === Dataclass Domain Entity ===


@dataclass(frozen=True, kw_only=True)
class OpenAlexPublicationEntity(PublicationEntityBase):
    """Represents a scholarly publication from OpenAlex.

    Domain entity with lineage fields (run_id, content_hash, etc.).
    Inherits common publication fields from PublicationEntityBase.
    For DTO without lineage, use OpenAlexPublicationRecord.

    Terminology:
    - Uses "Publication" instead of OpenAlex API term "Work" for Ubiquitous Language
    - Business analysts can understand the model without knowing OpenAlex API specifics

    Inherited from PublicationEntityBase:
        doi, pmid, title, abstract, authors, journal, issn, publisher,
        year, publication_date, citation_count, doc_type, language, is_oa,
        oa_status, _lookup_method, _original_id.

    OpenAlex-specific Attributes:
        openalex_id: OpenAlex Work ID (e.g., W2148763428). REQUIRED.
        concepts: Top concept names from OpenAlex.

    Note: openalex_id is required for OpenAlex publications.

    See: https://docs.openalex.org/api-entities/works
    """

    # Primary identifier (OpenAlex Work ID) - REQUIRED
    openalex_id: str

    # External identifiers (in addition to inherited doi, pmid, pmc_id)
    mag_id: str | None = None  # Microsoft Academic Graph ID

    # OpenAlex-specific: Concepts (top-level only)
    concepts: list[str] = field(default_factory=list)

    # MeSH terms (Medical Subject Headings)
    mesh: list[str] = field(default_factory=list)

    # Keywords (author-assigned)
    keywords: list[str] = field(default_factory=list)

    # Bibliographic info (from biblio object)
    volume: str | None = None
    issue: str | None = None

    # Additional metrics
    fwci: float | None = None  # Field-Weighted Citation Impact
    referenced_works_count: int | None = None

    # Quality indicators
    is_retracted: bool = False

    # Note: _source is set by transformer via entity_to_silver_record() mapping

    def __post_init__(self) -> None:
        """Post-initialization validation.

        Validates that openalex_id is provided (required for OpenAlex publications).
        """
        super().__post_init__()
        if not self.openalex_id:
            raise ValueError("OpenAlex Publication ID is required")


__all__ = [
    "LOOKUP_METHODS",
    "OPENALEX_TYPE_MAP",
    "OpenAlexPublicationEntity",
    "OpenAlexPublicationRecord",
]
