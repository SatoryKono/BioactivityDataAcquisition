"""CrossRef domain entities.

Contains:
- PublicationRecord: DTO (Pydantic) for type-safe data transfer at boundaries
- CrossRefPublicationEntity: Domain entity (dataclass) with lineage fields

DTO Design:
- Uses extra='forbid' to detect API changes early
- frozen=True ensures immutability
- Adapters return DTOs, transformers convert to Domain Entities

Terminology:
- Uses "Publication" instead of CrossRef API term "Work" for Ubiquitous Language
- All layers use "publication" to refer to scholarly works (articles, preprints, etc.)

Used for enriching publication records with DOI resolution and citation metadata.

Note: CrossRefPublicationEntity inherits common fields from PublicationEntityBase.
Provider-specific fields (volume, issue, pages, etc.) are defined here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField

from bioetl.domain.entities.publication_base import PublicationEntityBase

# Document type mapping from CrossRef types to internal types
CROSSREF_TYPE_MAP = {
    "journal-article": "PUBLICATION",
    "posted-content": "PREPRINT",
    "proceedings-article": "PUBLICATION",
    "book-chapter": "PUBLICATION",
    "dissertation": "PUBLICATION",
}


# === Pydantic DTO Model ===


class PublicationRecord(BaseModel):
    """Scholarly work DTO from CrossRef.

    Represents publication metadata from CrossRef API for DOI resolution
    and citation enrichment.

    Required field: doi.

    Example:
        >>> record = PublicationRecord(
        ...     doi="10.1038/nature12373",
        ...     title="Example Article",
        ...     journal="Nature",
        ...     year=2013,
        ... )
        >>> record.model_dump()
        {'doi': '10.1038/nature12373', 'title': 'Example Article', ...}

    See: https://api.crossref.org/swagger-ui/index.html
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED, normalized DOI - lowercase, stripped)
    doi: str = PydanticField(description="Digital Object Identifier (normalized)")

    # Core metadata
    title: str | None = PydanticField(default=None, description="Publication title")
    abstract: str | None = PydanticField(
        default=None, description="Publication abstract"
    )

    # Authors (JSON-serialized list of hashed names for PII compliance)
    authors: str | None = PydanticField(
        default=None, description="Author names (JSON array, hashed for PII)"
    )

    # Journal information
    journal: str | None = PydanticField(
        default=None, description="Container title (journal name)"
    )
    issn: list[str] = PydanticField(default_factory=list, description="ISSN list")
    publisher: str | None = PydanticField(default=None, description="Publisher name")

    # Publication details
    volume: str | None = PydanticField(default=None, description="Volume number")
    issue: str | None = PydanticField(default=None, description="Issue number")
    first_page: str | None = PydanticField(default=None, description="First page")
    last_page: str | None = PydanticField(default=None, description="Last page")

    # Dates
    year: int | None = PydanticField(default=None, description="Publication year")
    published_print: str | None = PydanticField(
        default=None, description="Print publication date (ISO format)"
    )
    published_online: str | None = PydanticField(
        default=None, description="Online publication date (ISO format)"
    )

    # Document type (mapped from CrossRef type)
    doc_type: str = PydanticField(
        default="PUBLICATION", description="Document type (PUBLICATION or PREPRINT)"
    )

    # Citation metrics
    citation_count: int | None = PydanticField(
        default=None, description="Times cited (is-referenced-by-count)"
    )
    reference_count: int | None = PydanticField(
        default=None, description="Number of references (references-count)"
    )

    # Additional metadata
    language: str | None = PydanticField(
        default=None, description="Primary language code"
    )
    license_url: str | None = PydanticField(default=None, description="License URL")
    subjects: list[str] = PydanticField(
        default_factory=list, description="Subject areas"
    )

    # Source tracking
    source: str = PydanticField(default="crossref", description="Data source")


# === Dataclass Domain Entity ===


@dataclass(frozen=True, kw_only=True)
class CrossRefPublicationEntity(PublicationEntityBase):
    """Represents a scholarly publication from CrossRef.

    Domain entity with lineage fields (run_id, content_hash, etc.).
    Inherits common publication fields from PublicationEntityBase.
    For DTO without lineage, use PublicationRecord.

    Terminology:
    - Uses "Publication" instead of CrossRef API term "Work" for Ubiquitous Language
    - Business analysts can understand the model without knowing CrossRef API specifics

    Inherited from PublicationEntityBase:
        doi, pmid, title, abstract, authors, journal, issn (str), publisher,
        year, publication_date, citation_count, doc_type, language, is_oa,
        oa_status, _lookup_method, _original_doi, source.

    CrossRef-specific Attributes:
        issn: List of ISSNs (overrides base str|None with list[str]).
        volume: Volume number.
        issue: Issue number.
        first_page: First page number.
        last_page: Last page number.
        published_print: Print publication date (ISO format).
        published_online: Online publication date (ISO format).
        reference_count: Number of references in the publication.
        license_url: License URL.
        subjects: Subject areas.

    Note: doi is required for CrossRef publications and validated in __post_init__.

    See: https://api.crossref.org/swagger-ui/index.html
    """

    # Override: DOI is REQUIRED for CrossRef (base has Optional)
    doi: str

    # Override: ISSN as list (base has str|None)
    # CrossRef returns multiple ISSNs (print/electronic), other providers return single ISSN
    issn: list[str] = field(default_factory=list)  # type: ignore[assignment]

    # CrossRef-specific publication details
    volume: str | None = None
    issue: str | None = None
    first_page: str | None = None
    last_page: str | None = None

    # CrossRef-specific dates
    published_print: str | None = None  # ISO date: YYYY-MM-DD or YYYY-MM or YYYY
    published_online: str | None = None  # ISO date

    # CrossRef-specific metrics
    reference_count: int | None = None  # references-count

    # CrossRef-specific metadata
    license_url: str | None = None
    subjects: list[str] = field(default_factory=list)

    # Override: Default source for CrossRef
    source: str = "crossref"

    def __post_init__(self) -> None:
        """Post-initialization validation.

        Validates that DOI is provided (required for CrossRef publications).
        """
        super().__post_init__()
        if not self.doi:
            raise ValueError("CrossRef Publication DOI is required")


# Deprecated alias for backward compatibility
PublicationEntity = CrossRefPublicationEntity

__all__ = [
    "CROSSREF_TYPE_MAP",
    "CrossRefPublicationEntity",
    "PublicationEntity",
    "PublicationRecord",
]
