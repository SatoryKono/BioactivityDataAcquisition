"""PubMed domain entities.

Contains entities for PubMed data: Publication.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.domain.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class Publication(BaseEntity):
    """Represents a scientific publication from PubMed.

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

    # Authors
    authors: list[str] = field(default_factory=list)

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
