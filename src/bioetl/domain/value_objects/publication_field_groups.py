"""Publication field group definitions for Composite Publication Pipeline.

Defines semantic grouping of publication fields across providers for:
- Column ordering in merged output
- Gold layer filtering (excluding trash group)
- Analytical views and reporting

See ADR-026 for Composite Publication Pipeline rationale.

Providers:
- ChEMBL (seed)
- CrossRef, OpenAlex, PubMed, SemanticScholar (enrichers)

Field naming convention: {provider}.publication.{field}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Final

__all__ = [
    "DEFAULT_FIELD_GROUP_CONFIG",
    "FIELD_TO_GROUP_MAPPING",
    "FieldGroupConfig",
    "PublicationFieldGroup",
]


class PublicationFieldGroup(str, Enum):
    """Semantic groups for publication fields.

    Groups are used for:
    1. Column ordering in composite output (groups appear in enum order)
    2. Gold layer filtering (trash group is excluded)
    3. Analytical views and field selection

    Attributes:
        ID_AND_STATUS: Identifiers, DOIs, PMIDs, status flags
        BIBLIOGRAPHY: Title, abstract, journal, volume, issue, pages
        AUTHOR_AND_AFFILIATIONS: Authors, affiliations, institutions
        TERMS_AND_KEYWORDS_AND_TOPICS: Keywords, MeSH, topics, classification
        CITATIONS_AND_REFERENCE: Citation counts, references
        DATE_AND_PLACES: Publication dates, countries, locations
        PUBLICATION_TYPES: Document types, publication types
        TRASH: Excluded from Gold layer (internal, redundant, low-value)
    """

    ID_AND_STATUS = "id_and_status"
    BIBLIOGRAPHY = "bibliography"
    AUTHOR_AND_AFFILIATIONS = "author_and_affiliations"
    TERMS_AND_KEYWORDS_AND_TOPICS = "terms_and_keywords_and_topics"
    CITATIONS_AND_REFERENCE = "citations_and_reference"
    DATE_AND_PLACES = "date_and_places"
    PUBLICATION_TYPES = "publication_types"
    TRASH = "trash"

    @property
    def display_name(self) -> str:
        """Human-readable display name for the group."""
        return _GROUP_DISPLAY_NAMES[self]

    @property
    def include_in_gold(self) -> bool:
        """Check if fields in this group should be included in Gold layer."""
        return self != PublicationFieldGroup.TRASH

    @classmethod
    def from_string(cls, value: str) -> PublicationFieldGroup:
        """Parse group from string value.

        Args:
            value: Group identifier (case-insensitive).

        Returns:
            Matching PublicationFieldGroup.

        Raises:
            ValueError: If value doesn't match any group.
        """
        normalized = value.lower().strip()
        try:
            return cls(normalized)
        except ValueError:
            valid = ", ".join(g.value for g in cls)
            raise ValueError(
                f"Invalid field group: '{value}'. Valid groups: {valid}"
            ) from None

    @classmethod
    def gold_groups(cls) -> tuple[PublicationFieldGroup, ...]:
        """Get all groups that should be included in Gold layer."""
        return tuple(g for g in cls if g.include_in_gold)

    @classmethod
    def excluded_groups(cls) -> tuple[PublicationFieldGroup, ...]:
        """Get all groups excluded from Gold layer."""
        return tuple(g for g in cls if not g.include_in_gold)


# Display names for each group
_GROUP_DISPLAY_NAMES: Final[dict[PublicationFieldGroup, str]] = {
    PublicationFieldGroup.ID_AND_STATUS: "ID & Status",
    PublicationFieldGroup.BIBLIOGRAPHY: "Bibliography",
    PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS: "Author & Affiliations",
    PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS: "Terms & Keywords & Topics",
    PublicationFieldGroup.CITATIONS_AND_REFERENCE: "Citations & Reference",
    PublicationFieldGroup.DATE_AND_PLACES: "Date & Places",
    PublicationFieldGroup.PUBLICATION_TYPES: "Publication Types",
    PublicationFieldGroup.TRASH: "Trash (Excluded)",
}


# Field base name to group mapping
# Keys are base field names (without provider.entity prefix)
# This mapping covers all fields from 5 providers:
# - chembl, crossref, openalex, pubmed, semanticscholar
#
# Entries are ordered by canonical category (docs/schemas/publication_field_order.csv):
#   id → bibliography → author_and_affiliation → date →
#   topics_and_keywords → publication
FIELD_TO_GROUP_MAPPING: Final[dict[str, PublicationFieldGroup]] = {
    # ===== canonical: id (1-24) =====
    "alternative_id": PublicationFieldGroup.ID_AND_STATUS,
    "chembl_release": PublicationFieldGroup.ID_AND_STATUS,
    "content_hash": PublicationFieldGroup.TRASH,
    "corpus_id": PublicationFieldGroup.ID_AND_STATUS,
    "dblp_id": PublicationFieldGroup.TRASH,
    "document_chembl_id": PublicationFieldGroup.ID_AND_STATUS,
    "doi": PublicationFieldGroup.ID_AND_STATUS,
    "entity_id": PublicationFieldGroup.ID_AND_STATUS,
    "mag_id": PublicationFieldGroup.ID_AND_STATUS,
    "nlm_unique_id": PublicationFieldGroup.ID_AND_STATUS,
    "openalex_id": PublicationFieldGroup.ID_AND_STATUS,
    "paper_id": PublicationFieldGroup.ID_AND_STATUS,
    "pmc_id": PublicationFieldGroup.ID_AND_STATUS,
    "pmid": PublicationFieldGroup.ID_AND_STATUS,
    "src_id": PublicationFieldGroup.TRASH,
    # ===== canonical: bibliography (25-83) =====
    "abstract": PublicationFieldGroup.BIBLIOGRAPHY,
    "abstract_structured": PublicationFieldGroup.TRASH,
    "issn": PublicationFieldGroup.BIBLIOGRAPHY,
    "issn_electronic": PublicationFieldGroup.BIBLIOGRAPHY,
    "issn_list": PublicationFieldGroup.BIBLIOGRAPHY,
    "issn_print": PublicationFieldGroup.BIBLIOGRAPHY,
    "issue": PublicationFieldGroup.BIBLIOGRAPHY,
    "journal": PublicationFieldGroup.BIBLIOGRAPHY,
    "journal_full_title": PublicationFieldGroup.BIBLIOGRAPHY,
    "journal_iso_abbrev": PublicationFieldGroup.BIBLIOGRAPHY,
    "journal_issn_type": PublicationFieldGroup.BIBLIOGRAPHY,
    "journal_name_short": PublicationFieldGroup.BIBLIOGRAPHY,
    "page_first": PublicationFieldGroup.BIBLIOGRAPHY,
    "page_last": PublicationFieldGroup.BIBLIOGRAPHY,
    "page_range": PublicationFieldGroup.BIBLIOGRAPHY,
    "published": PublicationFieldGroup.DATE_AND_PLACES,
    "published_online": PublicationFieldGroup.DATE_AND_PLACES,
    "published_print": PublicationFieldGroup.DATE_AND_PLACES,
    "publisher": PublicationFieldGroup.BIBLIOGRAPHY,
    "publication_year": PublicationFieldGroup.DATE_AND_PLACES,
    "title": PublicationFieldGroup.BIBLIOGRAPHY,
    "venue": PublicationFieldGroup.BIBLIOGRAPHY,
    "volume": PublicationFieldGroup.BIBLIOGRAPHY,
    # ===== canonical: author_and_affiliation (84-104) =====
    "affiliation_list": PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS,
    "affiliation_structured": PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS,
    "author_count": PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS,
    "author_details": PublicationFieldGroup.TRASH,
    "author_h_indices": PublicationFieldGroup.TRASH,
    "author_openalex_ids": PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS,
    "author_orcid_list": PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS,
    "author_orcids": PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS,
    "author_s2_ids": PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS,
    "authors": PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS,
    "authors_with_affiliations": PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS,
    "country": PublicationFieldGroup.DATE_AND_PLACES,
    "institution_country_codes": PublicationFieldGroup.DATE_AND_PLACES,
    "institution_ids": PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS,
    "ror_ids": PublicationFieldGroup.TRASH,
    # ===== canonical: date (105-114) =====
    "creation_date": PublicationFieldGroup.DATE_AND_PLACES,
    "date_completed": PublicationFieldGroup.DATE_AND_PLACES,
    "date_revised": PublicationFieldGroup.DATE_AND_PLACES,
    "pub_date": PublicationFieldGroup.DATE_AND_PLACES,
    "pub_day": PublicationFieldGroup.TRASH,
    "pub_month": PublicationFieldGroup.DATE_AND_PLACES,
    "publication_date": PublicationFieldGroup.DATE_AND_PLACES,
    # ===== canonical: topics_and_keywords (115-130) =====
    "chemical_count": PublicationFieldGroup.CITATIONS_AND_REFERENCE,
    "chemicals": PublicationFieldGroup.TRASH,
    "citation_subset": PublicationFieldGroup.CITATIONS_AND_REFERENCE,
    "databanks": PublicationFieldGroup.TRASH,
    "fwci": PublicationFieldGroup.TRASH,
    "gene_symbols": PublicationFieldGroup.TRASH,
    "keyword_count": PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS,
    "mesh": PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS,
    "mesh_heading_count": PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS,
    "primary_topic": PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS,
    "subject_fields": PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS,
    "subject_keywords": PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS,
    "subject_mesh": PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS,
    "subject_topics": PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS,
    # ===== canonical: publication (131-167) =====
    "citation_contexts": PublicationFieldGroup.TRASH,
    "citations_made": PublicationFieldGroup.CITATIONS_AND_REFERENCE,
    "citations_received": PublicationFieldGroup.CITATIONS_AND_REFERENCE,
    "content_domain_crossmark_restriction": PublicationFieldGroup.TRASH,
    "content_domain_domains": PublicationFieldGroup.TRASH,
    "grant_count": PublicationFieldGroup.TRASH,
    "grants": PublicationFieldGroup.TRASH,
    "influential_citation_count": PublicationFieldGroup.TRASH,
    "is_oa": PublicationFieldGroup.ID_AND_STATUS,
    "is_retracted": PublicationFieldGroup.ID_AND_STATUS,
    "language": PublicationFieldGroup.TRASH,
    "license_url": PublicationFieldGroup.TRASH,
    "medline_pgn": PublicationFieldGroup.TRASH,
    "oa_status": PublicationFieldGroup.ID_AND_STATUS,
    "open_access_url": PublicationFieldGroup.ID_AND_STATUS,
    "publication_status": PublicationFieldGroup.ID_AND_STATUS,
    "publication_type": PublicationFieldGroup.ID_AND_STATUS,
    "publication_type_list": PublicationFieldGroup.PUBLICATION_TYPES,
    "publication_types": PublicationFieldGroup.PUBLICATION_TYPES,
    "references": PublicationFieldGroup.TRASH,
    "tldr": PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS,
}


@dataclass(frozen=True, slots=True)
class FieldGroupConfig:
    """Configuration for field grouping operations.

    Provides lookup and filtering capabilities for publication fields
    based on semantic groups.

    Attributes:
        field_groups: Mapping of field base names to groups.
        provider_priority: Order of providers for column ordering within groups.
        default_group: Group for unmapped fields (default: TRASH).

    Example:
        >>> config = FieldGroupConfig()
        >>> config.get_group("title")
        <PublicationFieldGroup.BIBLIOGRAPHY: 'bibliography'>
        >>> config.get_group("chembl.publication.doi")
        <PublicationFieldGroup.ID_AND_STATUS: 'id_and_status'>
        >>> config.is_gold_field("content_hash")
        False
    """

    field_groups: dict[str, PublicationFieldGroup] = field(
        default_factory=lambda: dict(FIELD_TO_GROUP_MAPPING)
    )
    provider_priority: tuple[str, ...] = (
        "chembl",
        "crossref",
        "openalex",
        "pubmed",
        "semanticscholar",
    )
    default_group: PublicationFieldGroup = PublicationFieldGroup.TRASH

    def get_group(self, column: str) -> PublicationFieldGroup:
        """Get semantic group for a column.

        Handles both qualified (provider.entity.field) and
        unqualified (field) column names.

        Args:
            column: Column name (qualified or unqualified).

        Returns:
            PublicationFieldGroup for the column.
        """
        field_name = self._extract_field(column)
        return self.field_groups.get(field_name, self.default_group)

    def is_gold_field(self, column: str) -> bool:
        """Check if a column should be included in Gold layer.

        Args:
            column: Column name (qualified or unqualified).

        Returns:
            True if field should be included in Gold layer.
        """
        return self.get_group(column).include_in_gold

    def get_gold_columns(self, columns: list[str]) -> list[str]:
        """Filter columns to only those included in Gold layer.

        Args:
            columns: List of column names.

        Returns:
            Filtered list of columns (Gold layer only).
        """
        return [c for c in columns if self.is_gold_field(c)]

    def get_trash_columns(self, columns: list[str]) -> list[str]:
        """Get columns that would be excluded from Gold layer.

        Args:
            columns: List of column names.

        Returns:
            List of trash columns.
        """
        return [c for c in columns if not self.is_gold_field(c)]

    def get_columns_by_group(
        self, columns: list[str], group: PublicationFieldGroup
    ) -> list[str]:
        """Get columns belonging to a specific group.

        Args:
            columns: List of column names.
            group: Target group.

        Returns:
            Columns belonging to the specified group.
        """
        return [c for c in columns if self.get_group(c) == group]

    def group_columns(
        self, columns: list[str]
    ) -> dict[PublicationFieldGroup, list[str]]:
        """Group columns by their semantic groups.

        Args:
            columns: List of column names.

        Returns:
            Dictionary mapping groups to their columns.
        """
        result: dict[PublicationFieldGroup, list[str]] = {
            g: [] for g in PublicationFieldGroup
        }
        for column in columns:
            group = self.get_group(column)
            result[group].append(column)
        return result

    def get_provider_rank(self, column: str) -> int:
        """Get provider rank for ordering within semantic group.

        Args:
            column: Column name (qualified or unqualified).

        Returns:
            Provider rank (lower = higher priority).
            Returns -1 for unqualified columns (seed).
            Returns 999 for unknown providers.
        """
        parts = column.split(".")
        if len(parts) == 3:
            provider = parts[0].lower()
            try:
                return self.provider_priority.index(provider)
            except ValueError:
                return 999
        return -1

    def sort_columns(self, columns: list[str]) -> list[str]:
        """Sort columns by semantic group and provider priority.

        Columns are sorted by:
        1. Semantic group (enum order)
        2. Provider priority (seed first, then by provider_priority)
        3. Field name (alphabetical)

        Args:
            columns: List of column names to sort.

        Returns:
            Sorted list of columns.
        """

        def sort_key(column: str) -> tuple[int, int, str]:
            group = self.get_group(column)
            provider_rank = self.get_provider_rank(column)
            field_name = self._extract_field(column)
            return (list(PublicationFieldGroup).index(group), provider_rank, field_name)

        return sorted(columns, key=sort_key)

    def _extract_field(self, column: str) -> str:
        """Extract field name from column (qualified or unqualified).

        Args:
            column: Column name.

        Returns:
            Base field name.
        """
        parts = column.split(".")
        if len(parts) == 3:
            return parts[2].lower()
        return column.lower()

    def get_field_providers(self, field_name: str) -> list[str]:
        """Get providers that supply a given field.

        Based on the mapping, returns which providers have this field.

        Args:
            field_name: Base field name (e.g., "title", "doi").

        Returns:
            List of provider names that have this field.

        Note:
            This returns providers from provider_priority that are expected
            to have this field. For exact provider coverage, see the
            field mapping documentation.
        """
        # This is a simplified implementation
        # Full implementation would track provider->field mapping
        normalized = field_name.lower()
        if normalized in self.field_groups:
            # Return all providers in priority order
            # Real implementation should filter by actual field presence
            return list(self.provider_priority)
        return []


# Default configuration instance
DEFAULT_FIELD_GROUP_CONFIG: Final[FieldGroupConfig] = FieldGroupConfig()
