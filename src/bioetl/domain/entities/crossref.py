"""CrossRef domain entities.

Contains:
- PublicationRecord: DTO (Pydantic) for type-safe data transfer at boundaries
- Work: Domain entity (dataclass) with lineage fields - deprecated, use PublicationRecord

DTO Design:
- Uses extra='forbid' to detect API changes early
- frozen=True ensures immutability
- Adapters return DTOs, transformers convert to Domain Entities

Used for enriching publication records with DOI resolution and citation metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField

from bioetl.domain.entities.base import BaseEntity

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
    title: str | None = PydanticField(default=None, description="Work title")
    abstract: str | None = PydanticField(default=None, description="Work abstract")

    # Authors (list of "given family" formatted names)
    authors: list[str] = PydanticField(
        default_factory=list, description="Author names"
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


# === Dataclass Domain Entity (backward compatibility) ===


@dataclass(frozen=True, kw_only=True)
class Work(BaseEntity):
    """Represents a scholarly work from CrossRef.

    Domain entity with lineage fields (run_id, content_hash, etc.).
    For DTO without lineage, use PublicationRecord.

    Note: This class is kept for backward compatibility.
    New code should use PublicationRecord DTO.

    See: https://api.crossref.org/swagger-ui/index.html
    """

    # Primary identifier (normalized DOI - lowercase, stripped)
    doi: str

    # Core metadata
    title: str | None = None
    abstract: str | None = None

    # Authors (list of "given family" formatted names)
    authors: list[str] = field(default_factory=list)

    # Journal information
    journal: str | None = None  # container-title[0]
    issn: list[str] = field(default_factory=list)  # ISSN list
    publisher: str | None = None

    # Publication details
    volume: str | None = None
    issue: str | None = None
    first_page: str | None = None
    last_page: str | None = None

    # Dates
    year: int | None = None  # Published year
    published_print: str | None = None  # ISO date: YYYY-MM-DD or YYYY-MM or YYYY
    published_online: str | None = None  # ISO date

    # Document type (mapped from CrossRef type)
    doc_type: str = "PUBLICATION"  # PUBLICATION or PREPRINT

    # Citation metrics
    citation_count: int | None = None  # is-referenced-by-count
    reference_count: int | None = None  # references-count

    # Additional metadata
    language: str | None = None
    license_url: str | None = None
    subjects: list[str] = field(default_factory=list)

    # Source tracking
    source: str = "crossref"

    def __post_init__(self) -> None:
        """Post-initialization validation."""
        super().__post_init__()
        if not self.doi:
            raise ValueError("CrossRef Work DOI is required")


__all__ = ["CROSSREF_TYPE_MAP", "PublicationRecord", "Work"]
