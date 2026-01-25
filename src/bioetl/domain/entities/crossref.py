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

# Document type mapping from CrossRef types to BioETL unified types.
# See: https://api.crossref.org/types for complete list (30 types).
#
# Unified types (aligned with chembl/publication.py schema):
# - PUBLICATION: Journal articles, conference papers, peer reviews
# - BOOK: Books, monographs, book chapters, dissertations, reference entries
# - PREPRINT: Pre-publication works (posted-content)
# - DATASET: Research data and databases
# - OTHER: Reports, standards, container types, supplementary materials, funding
#
# Rationale:
# - BOOK includes dissertations (thesis = monograph) and reference entries
# - Reports/standards → OTHER (technical documents, not scholarly publications)
# - "component" → OTHER (supplementary material, not standalone scholarly work)
# - Container types → OTHER (metadata records, not scholarly content)
CROSSREF_TYPE_MAP: dict[str, str] = {
    # === Journal/Conference Articles → PUBLICATION ===
    "journal-article": "PUBLICATION",
    "proceedings-article": "PUBLICATION",
    "peer-review": "PUBLICATION",  # Published peer review
    "other": "PUBLICATION",  # Unclassified scholarly work
    # === Books & Book Parts → BOOK ===
    "book": "BOOK",
    "monograph": "BOOK",
    "edited-book": "BOOK",
    "reference-book": "BOOK",  # Dictionary, encyclopedia
    "book-chapter": "BOOK",
    "book-section": "BOOK",
    "book-part": "BOOK",
    "book-track": "BOOK",  # Audio book track
    "dissertation": "BOOK",  # Thesis/monograph
    "reference-entry": "BOOK",  # Dictionary/encyclopedia entry
    # === Pre-publication → PREPRINT ===
    "posted-content": "PREPRINT",
    # === Research Data → DATASET ===
    "dataset": "DATASET",
    "database": "DATASET",
    # === Reports & Standards → OTHER ===
    "report": "OTHER",  # Technical report
    "report-component": "OTHER",  # Part of a report
    "standard": "OTHER",  # Technical standard
    # === Supplementary Material → OTHER ===
    "component": "OTHER",  # Figures, tables, supplementary files
    # === Container/Series Types → OTHER ===
    # (Metadata records for series, not individual works)
    "journal": "OTHER",
    "journal-volume": "OTHER",
    "journal-issue": "OTHER",
    "proceedings": "OTHER",
    "proceedings-series": "OTHER",
    "book-series": "OTHER",
    "book-set": "OTHER",
    "report-series": "OTHER",
    # === Funding → OTHER ===
    "grant": "OTHER",
}

# Default type for unknown CrossRef types (conservative fallback)
CROSSREF_TYPE_DEFAULT = "PUBLICATION"


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
        oa_status, _lookup_method, _original_id, source.

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
    # first_page and last_page inherited from PublicationEntityBase

    # CrossRef-specific dates
    published_print: str | None = None  # ISO date: YYYY-MM-DD or YYYY-MM or YYYY
    published_online: str | None = None  # ISO date

    # CrossRef-specific metrics
    reference_count: int | None = None  # references-count

    # CrossRef-specific metadata
    license_url: str | None = None
    subjects: list[str] = field(default_factory=list)

    # Content domain (Crossmark/license restrictions)
    content_domain_domains: list[str] = field(default_factory=list)
    content_domain_crossmark_restriction: bool | None = None

    # Alternative identifiers (publisher-specific IDs, e.g., PII)
    alternative_id: list[str] = field(default_factory=list)

    # Canonical publication date (preferred over print/online)
    published: str | None = None

    # Short journal/container title
    short_container_title: list[str] = field(default_factory=list)

    # ISSN by type (split from generic ISSN list)
    issn_print: str | None = None
    issn_electronic: str | None = None

    # Override: Default source for CrossRef
    source: str = "crossref"

    def __post_init__(self) -> None:
        """Post-initialization validation.

        Validates that DOI is provided (required for CrossRef publications).
        """
        super().__post_init__()
        if not self.doi:
            raise ValueError("CrossRef Publication DOI is required")


__all__ = [
    "CROSSREF_TYPE_DEFAULT",
    "CROSSREF_TYPE_MAP",
    "CrossRefPublicationEntity",
    "PublicationRecord",
]
