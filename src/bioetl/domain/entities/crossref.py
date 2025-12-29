"""CrossRef domain entities.

Contains entities for CrossRef data: Work (publication metadata).
Used for enriching publication records with DOI resolution and citation metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.domain.entities.base import BaseEntity

# Document type mapping from CrossRef types to internal types
CROSSREF_TYPE_MAP = {
    "journal-article": "PUBLICATION",
    "posted-content": "PREPRINT",
    "proceedings-article": "PUBLICATION",
    "book-chapter": "PUBLICATION",
    "dissertation": "PUBLICATION",
}


@dataclass(frozen=True, kw_only=True)
class Work(BaseEntity):
    """Represents a scholarly work from CrossRef.

    Contains metadata retrieved from CrossRef API for DOI resolution
    and citation enrichment.

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
