"""OpenAlex domain entities.

Contains OpenAlexPublicationEntity (domain).
Topics provide a 4-level hierarchy: domain -> field -> subfield -> topic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.domain.entities.publication_base import PublicationEntityBase
from bioetl.domain.immutability import freeze_fields
from bioetl.domain.schemas.common.publication_base import LOOKUP_METHODS
from bioetl.domain.types import JsonDict

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
    author_openalex_ids: str | None = (
        None  # OpenAlex author IDs (empty string for missing)
    )

    # Topics (hierarchical classification - replaces deprecated concepts)
    # Each topic dict has: id, display_name, score, subfield, field, domain
    subject_topics: list[JsonDict] = field(default_factory=list)

    # Primary topic (single most relevant topic for quick categorization)
    # Dict with: id, display_name, score, subfield, field, domain
    primary_topic: JsonDict | None = None

    # Grants/funding information
    # Each grant dict has: funder, funder_display_name, award_id
    grants: list[JsonDict] = field(default_factory=list)

    # MeSH terms (Medical Subject Headings)
    subject_mesh: list[str] = field(default_factory=list)

    # Keywords (author-assigned)
    subject_keywords: list[str] = field(default_factory=list)

    # Bibliographic info (from biblio object)
    volume: str | None = None
    issue: str | None = None

    # Additional metrics
    fwci: float | None = None  # Field-Weighted Citation Impact

    # Quality indicators
    is_retracted: bool = False

    # Note: publication_type inherited from PublicationEntityBase
    # Stores raw OpenAlex type (e.g., "article", "preprint", "book-chapter")
    type_crossref: str | None = None

    # Override: Default source for OpenAlex
    _source: str = "openalex"

    def __post_init__(self) -> None:
        super().__post_init__()
        freeze_fields(
            self,
            (
                "institution_ids",
                "institution_country_codes",
                "ror_ids",
                "subject_topics",
                "primary_topic",
                "grants",
                "subject_mesh",
                "subject_keywords",
            ),
        )

    def _validate_invariants(self) -> None:
        """Validate OpenAlex-specific publication invariants."""
        super()._validate_invariants()
        if not self.openalex_id:
            raise ValueError("OpenAlex Publication ID is required")


__all__ = [
    "LOOKUP_METHODS",
    "OpenAlexPublicationEntity",
]
