"""OpenAlex domain entities.

Contains entities for OpenAlex data: OpenAlexWork.

See: https://docs.openalex.org/api-entities/works
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.domain.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class OpenAlexWork(BaseEntity):
    """Represents a scholarly work from OpenAlex.

    Contains comprehensive metadata from OpenAlex open index.
    See: https://docs.openalex.org/api-entities/works

    Primary Key: openalex_id (W-prefixed, e.g., W2741809807)
    """

    # Primary identifier (REQUIRED)
    openalex_id: str

    # Required fields
    display_name: str  # Title
    type: str  # article, book, etc.

    # External identifiers (API-OPTIONAL)
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    mag_id: str | None = None

    # Publication info
    publication_year: int | None = None
    publication_date: str | None = None  # ISO date string
    language: str | None = None

    # Primary location (flattened from nested structure)
    primary_location_source_id: str | None = None
    primary_location_source_name: str | None = None
    primary_location_source_issn: str | None = None
    primary_location_source_type: str | None = None
    primary_location_landing_page: str | None = None
    primary_location_pdf_url: str | None = None
    primary_location_version: str | None = None
    primary_location_license: str | None = None

    # Open Access
    is_oa: bool | None = None
    oa_status: str | None = None  # gold, green, hybrid, bronze, closed
    oa_url: str | None = None
    any_repository_has_fulltext: bool | None = None

    # Citations
    cited_by_count: int | None = None
    cited_by_percentile_year: float | None = None
    referenced_works_count: int | None = None

    # Bibliographic info
    biblio_volume: str | None = None
    biblio_issue: str | None = None
    biblio_first_page: str | None = None
    biblio_last_page: str | None = None

    # Flags
    is_retracted: bool | None = None
    is_paratext: bool | None = None
    has_fulltext: bool | None = None
    fulltext_origin: str | None = None

    # Abstract (reconstructed from inverted index)
    abstract: str | None = None
    abstract_inverted_index: str | None = None  # Original JSON for forensics

    # Primary Topic (flattened)
    primary_topic_id: str | None = None
    primary_topic_name: str | None = None
    primary_topic_score: float | None = None
    primary_topic_subfield: str | None = None
    primary_topic_field: str | None = None
    primary_topic_domain: str | None = None

    # Aggregated fields (joined strings)
    keywords: str | None = None
    sustainable_development_goals: str | None = None
    grants: str | None = None
    indexed_in: str | None = None
    related_works: str | None = None

    # Metrics
    fwci: float | None = None
    countries_distinct_count: int | None = None
    institutions_distinct_count: int | None = None

    # Corresponding authors
    corresponding_author_ids: str | None = None
    corresponding_institution_ids: str | None = None

    # Convenience fields (extracted/computed)
    authors: list[str] = field(default_factory=list)  # Author display names
    institutions: list[str] = field(default_factory=list)  # Institution names
    concept_names: list[str] = field(default_factory=list)  # Legacy concepts

    def __post_init__(self) -> None:
        """Post-initialization validation."""
        super().__post_init__()
        if not self.openalex_id:
            raise ValueError("OpenAlex work ID is required")
        if not self.openalex_id.startswith("W"):
            raise ValueError(
                f"OpenAlex work ID must start with 'W': {self.openalex_id}"
            )
        if not self.display_name:
            raise ValueError("Work display_name (title) is required")
        if not self.type:
            raise ValueError("Work type is required")
