# mypy: disable-error-code="misc"
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
from bioetl.domain.immutability import freeze_fields

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
    issn: list[str] = PydanticField(
        default_factory=list,
        description="ISSN values from CrossRef",
    )
    issn_list: str | None = PydanticField(
        default=None,
        description="Canonical JSON array of ISSN values",
    )
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

    def model_post_init(self, _context: object, /) -> None:
        """Detach and freeze nested DTO collections after validation."""
        freeze_fields(self, ("issn", "subjects"))

    # Note: _source is set by transformer via entity_to_silver_record() mapping


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

    Inherited from PublicationEntityBase (unified field names):
        doi, pmid, title, abstract, authors, affiliation_list, journal, issn, publisher,
        page_first, page_last, publication_year, publication_date,
        citations_received, citations_made, publication_type, language, is_oa,
        oa_status, _lookup_method, _original_id.

    CrossRef-specific Attributes:
        issn: ISSN values from CrossRef.
        issn_list: Canonical JSON array of all ISSNs.
        volume: Volume number.
        issue: Issue number.
        published_print: Print publication date (ISO format).
        published_online: Online publication date (ISO format).
        license_url: License URL.
        journal_name_short: Short journal/container title (unified field name).
        subject_keywords: Subject areas (unified field name).
        publication_type: Raw CrossRef type (e.g., "journal-article"), inherited from base.

    Note: doi is required for CrossRef publications and validated in __post_init__.

    See: https://api.crossref.org/swagger-ui/index.html
    """

    # Override: DOI is REQUIRED for CrossRef (base has Optional)
    doi: str

    # CrossRef domain entities preserve the native ISSN collection. Silver
    # normalization derives scalar issn and JSON issn_list for storage schemas.
    issn: list[str] = field(default_factory=list)
    issn_list: str | None = None

    # CrossRef-specific publication details
    volume: str | None = None
    issue: str | None = None
    # page_first and page_last inherited from PublicationEntityBase (unified names)

    # CrossRef-specific dates
    published_print: str | None = None  # ISO date: YYYY-MM-DD or YYYY-MM or YYYY
    published_online: str | None = None  # ISO date

    # CrossRef-specific metrics
    # Note: citations_received and citations_made inherited from base (unified names)
    # reference_count removed - mapped to citations_made in base

    # CrossRef-specific metadata
    license_url: str | None = None
    subject_keywords: list[str] = field(
        default_factory=list
    )  # Unified field name (was: subjects)

    # Content domain (Crossmark/license restrictions)
    content_domain_domains: list[str] = field(default_factory=list)
    content_domain_crossmark_restriction: bool | None = None

    # Alternative identifiers (publisher-specific IDs, e.g., PII)
    alternative_id: list[str] = field(default_factory=list)

    # Canonical publication date (preferred over print/online)
    published: str | None = None

    # Short journal/container title (unified field name)
    journal_name_short: str | None = None  # Was: short_container_title

    # ISSN by type (split from generic ISSN list)
    issn_print: str | None = None
    issn_electronic: str | None = None

    # Full author details with ORCID, sequence, affiliations (JSON array)
    author_details: str | None = None
    author_details_raw_json: str | None = None
    author_details_canonical_json: str | None = None

    # Bibliographic references (JSON array of citation data)
    references: str | None = None
    references_raw_json: str | None = None
    references_canonical_json: str | None = None

    # Note: publication_type inherited from PublicationEntityBase
    # Stores raw CrossRef type (e.g., "journal-article", "book-chapter")

    # Override: Default source for CrossRef
    _source: str = "crossref"

    def __post_init__(self) -> None:
        super().__post_init__()
        freeze_fields(
            self,
            ("issn", "subject_keywords", "content_domain_domains", "alternative_id"),
        )

    def _validate_invariants(self) -> None:
        """Validate CrossRef-specific publication invariants."""
        super()._validate_invariants()
        if not self.doi:
            raise ValueError("CrossRef Publication DOI is required")


__all__ = [
    "CrossRefPublicationEntity",
    "PublicationRecord",
]
