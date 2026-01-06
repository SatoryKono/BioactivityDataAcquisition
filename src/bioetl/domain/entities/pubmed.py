"""PubMed domain entities.

Contains:
- Publication: Domain entity (dataclass) with lineage fields
- ArticleRecord: DTO (Pydantic) for type-safe data transfer at boundaries

DTO Design:
- Uses extra='forbid' to detect API changes early
- frozen=True ensures immutability
- Adapters return DTOs, transformers convert to Domain Entities
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField

from bioetl.domain.entities.base import BaseEntity

# === Pydantic DTO Model ===


class ArticleRecord(BaseModel):
    """Scientific article DTO from PubMed.

    Represents article metadata extracted from PubMed XML via Entrez API.
    Required field: pmid.

    Example:
        >>> record = ArticleRecord(
        ...     pmid="12345678",
        ...     title="Example Article Title",
        ...     journal="Nature",
        ...     pub_year=2024,
        ... )
        >>> record.model_dump()
        {'pmid': '12345678', 'title': 'Example Article Title', ...}
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    pmid: str = PydanticField(description="PubMed ID")

    # Other identifiers
    doi: str | None = PydanticField(
        default=None, description="Digital Object Identifier"
    )
    pmc_id: str | None = PydanticField(default=None, description="PubMed Central ID")

    # Title and abstract
    title: str | None = PydanticField(default=None, description="Article title")
    abstract: str | None = PydanticField(default=None, description="Abstract text")

    # Journal information
    journal: str | None = PydanticField(default=None, description="Full journal title")
    journal_abbrev: str | None = PydanticField(
        default=None, description="Journal abbreviation (ISO)"
    )
    issn: str | None = PydanticField(default=None, description="ISSN")
    volume: str | None = PydanticField(default=None, description="Volume number")
    issue: str | None = PydanticField(default=None, description="Issue number")
    pages: str | None = PydanticField(default=None, description="Page numbers")

    # Authors (JSON-serialized list of hashed names for PII compliance)
    authors: str | None = PydanticField(
        default=None, description="Author names (JSON array, hashed for PII)"
    )

    # Dates (ISO format: YYYY-MM-DD or partial)
    pub_date: str | None = PydanticField(
        default=None, description="Publication date (ISO format)"
    )
    pub_year: int | None = PydanticField(
        default=None, description="Publication year (for partitioning)"
    )
    accepted_date: str | None = PydanticField(default=None, description="Date accepted")
    received_date: str | None = PydanticField(default=None, description="Date received")
    revised_date: str | None = PydanticField(default=None, description="Date revised")
    epub_date: str | None = PydanticField(
        default=None, description="Electronic publication date"
    )

    # Classification
    publication_types: list[str] = PydanticField(
        default_factory=list, description="Publication types"
    )
    keywords: list[str] = PydanticField(default_factory=list, description="Keywords")
    mesh_terms: list[str] = PydanticField(
        default_factory=list, description="MeSH terms"
    )

    # Additional metadata
    language: str | None = PydanticField(
        default=None, description="Primary language code"
    )
    country: str | None = PydanticField(
        default=None, description="Country of publication"
    )

    # Raw data for forensic (optional)
    raw_xml: str | None = PydanticField(
        default=None, description="Raw XML content (forensic)"
    )


# === Dataclass Domain Entity ===


@dataclass(frozen=True, kw_only=True)
class Publication(BaseEntity):
    """Represents a scientific publication from PubMed.

    Domain entity with lineage fields (run_id, content_hash, etc.).
    For DTO without lineage, use ArticleRecord.

    Contains comprehensive metadata extracted from PubMed XML via Entrez API.
    See: https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html
    """

    # Primary identifier
    pmid: str
    doi: str | None = None

    # Title and abstract
    title: str | None = None
    abstract: str | None = None

    # Journal information
    journal: str | None = None
    journal_abbrev: str | None = None
    issn: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None

    # Authors (JSON-serialized list of hashed names for PII compliance)
    authors: str | None = None

    # Dates (stored as ISO strings YYYY-MM-DD or partial YYYY-MM, YYYY)
    pub_date: str | None = None  # Publication date
    pub_year: int | None = None  # Publication year (for partitioning)
    accepted_date: str | None = None  # Date accepted
    received_date: str | None = None  # Date received
    revised_date: str | None = None  # Date revised
    epub_date: str | None = None  # Electronic publication date

    # Classification
    publication_types: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    mesh_terms: list[str] = field(default_factory=list)

    # Additional metadata
    language: str | None = None
    country: str | None = None
    pmc_id: str | None = None  # PubMed Central ID

    # Legacy field (kept for backward compatibility)
    publication_year: int | None = None  # Alias for pub_year

    def __post_init__(self) -> None:
        """Post-initialization validation."""
        super().__post_init__()
        if not self.pmid:
            raise ValueError("Publication PMID is required")


__all__ = ["ArticleRecord", "Publication"]
