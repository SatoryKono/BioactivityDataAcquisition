"""OpenAlex domain entities.

Contains OpenAlexPublicationRecord (DTO) and OpenAlexPublicationEntity (domain).
Topics provide a 4-level hierarchy: domain -> field -> subfield -> topic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
    """Scholarly work DTO from OpenAlex. Required field: openalex_id."""

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

    # Topics (hierarchical classification - replaces deprecated concepts)
    # Each topic dict has: id, display_name, score, subfield, field, domain
    topics: list[dict[str, Any]] = PydanticField(
        default_factory=list,
        description="Hierarchical topic classification (domain/field/subfield/topic)",
    )

    # Primary topic (single most relevant topic for quick categorization)
    # Dict with: id, display_name, score, subfield, field, domain
    primary_topic: dict[str, Any] | None = PydanticField(
        default=None, description="Primary topic classification"
    )

    # Grants/funding information
    # Each grant dict has: funder, funder_display_name, award_id
    grants: list[dict[str, Any]] = PydanticField(
        default_factory=list, description="Funding/grant information"
    )

    # MeSH terms (Medical Subject Headings)
    mesh_terms: list[str] = PydanticField(
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

    # Institution identifiers (for cross-referencing and geographic analysis)
    institution_ids: list[str] = PydanticField(
        default_factory=list,
        description="OpenAlex institution IDs (e.g., I1234567890)",
    )
    institution_country_codes: list[str] = PydanticField(
        default_factory=list,
        description="ISO 2-letter country codes of affiliated institutions",
    )
    ror_ids: list[str] = PydanticField(
        default_factory=list,
        description="ROR IDs of affiliated institutions (full URL format). "
        "May be empty if not returned by Works API.",
    )

    # Author identifiers (JSON-serialized lists preserving author order)
    author_orcids: str | None = PydanticField(
        default=None,
        description="ORCID IDs as JSON array (empty string for missing)",
    )
    author_openalex_ids: str | None = PydanticField(
        default=None,
        description="OpenAlex author IDs as JSON array (empty string for missing)",
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
    reference_count: int | None = PydanticField(
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
    """OpenAlex publication domain entity. Requires openalex_id."""

    # Primary identifier (OpenAlex Work ID) - REQUIRED
    openalex_id: str

    # External identifiers (in addition to inherited doi, pmid, pmc_id)
    mag_id: str | None = None  # Microsoft Academic Graph ID

    # Institution identifiers (for cross-referencing and geographic analysis)
    institution_ids: list[str] = field(default_factory=list)
    institution_country_codes: list[str] = field(default_factory=list)
    ror_ids: list[str] = field(default_factory=list)  # ROR IDs (may be empty)

    # Author identifiers (JSON-serialized lists preserving author order)
    author_orcids: str | None = None  # ORCID IDs (empty string for missing)
    author_openalex_ids: str | None = (
        None  # OpenAlex author IDs (empty string for missing)
    )

    # Topics (hierarchical classification - replaces deprecated concepts)
    # Each topic dict has: id, display_name, score, subfield, field, domain
    topics: list[dict[str, Any]] = field(default_factory=list)

    # Primary topic (single most relevant topic for quick categorization)
    # Dict with: id, display_name, score, subfield, field, domain
    primary_topic: dict[str, Any] | None = None

    # Grants/funding information
    # Each grant dict has: funder, funder_display_name, award_id
    grants: list[dict[str, Any]] = field(default_factory=list)

    # MeSH terms (Medical Subject Headings)
    mesh_terms: list[str] = field(default_factory=list)

    # Keywords (author-assigned)
    keywords: list[str] = field(default_factory=list)

    # Bibliographic info (from biblio object)
    volume: str | None = None
    issue: str | None = None

    # Additional metrics
    fwci: float | None = None  # Field-Weighted Citation Impact
    reference_count: int | None = None

    # Quality indicators
    is_retracted: bool = False

    # Raw document type from OpenAlex API (e.g., "article", "preprint", "book-chapter")
    # Unlike doc_type (unified mapping), this preserves the original OpenAlex type value
    source_type: str | None = None

    # Override: Default source for OpenAlex
    _source: str = "openalex"

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
