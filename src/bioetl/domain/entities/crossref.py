"""CrossRef domain entities.

Contains entities for CrossRef data: CrossRefPublication.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.domain.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class CrossRefPublication(BaseEntity):
    """Represents a scientific publication from CrossRef.

    Contains comprehensive metadata extracted from CrossRef API.
    See: https://api.crossref.org/swagger-ui/index.html

    Field Mapping from CrossRef API:
    - DOI -> doi (primary key)
    - title[0] -> title
    - author[].given + family -> authors
    - container-title[0] -> journal
    - published-print.date-parts[0] -> year
    - volume -> volume
    - page -> first_page (split by '-', take first)
    - abstract -> abstract (strip HTML tags)
    - is-referenced-by-count -> citation_count
    - type -> doc_type (map to PUBLICATION/PREPRINT)
    """

    # Primary identifier
    doi: str

    # Title and abstract
    title: str | None = None
    abstract: str | None = None

    # Authors (list of "Given Family" strings)
    authors: list[str] = field(default_factory=list)

    # Journal information
    journal: str | None = None
    issn: str | None = None
    volume: str | None = None
    issue: str | None = None
    first_page: str | None = None
    last_page: str | None = None

    # Dates
    year: int | None = None  # Publication year
    published_date: str | None = None  # Full date if available (YYYY-MM-DD)

    # Document type
    doc_type: str | None = None  # journal-article, proceedings-article, etc.

    # Citation metrics
    citation_count: int | None = None  # is-referenced-by-count
    references_count: int | None = None  # references-count

    # Publisher information
    publisher: str | None = None

    # Additional identifiers
    pmid: str | None = None  # PubMed ID if available
    pmc_id: str | None = None  # PubMed Central ID if available

    # Subject areas
    subjects: list[str] = field(default_factory=list)

    # Funder information (JSON serialized)
    funders: str | None = None  # JSON string of funder data

    # License information
    license_url: str | None = None

    # URL to full text
    url: str | None = None

    def __post_init__(self) -> None:
        """Post-initialization validation."""
        super().__post_init__()
        if not self.doi:
            raise ValueError("CrossRef Publication DOI is required")
