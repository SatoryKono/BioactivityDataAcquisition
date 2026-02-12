"""Column ordering configuration for semantic grouping.

Defines the order of columns in composite pipeline output.
See ADR-026 for rationale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import Final

__all__ = [
    "DEFAULT_COLUMN_ORDER",
    "PUBLICATION_FIELD_GROUPS",
    "ColumnOrderConfig",
    "SemanticGroup",
]


class SemanticGroup(IntEnum):
    """Semantic groups for column ordering.

    Lower values appear first in output.
    """

    SYSTEM = auto()  # entity_id, content_hash, _run_id, _ingestion_ts
    IDENTIFIERS = auto()  # document_chembl_id, doi, pmid, pmc_id
    TITLE = auto()  # title, *.title
    ABSTRACT = auto()  # abstract, *.abstract
    AUTHORS = auto()  # authors, *.authors, first_author
    JOURNAL = auto()  # journal, journal_name, source
    DATES = auto()  # publication_date, year, created_at
    METRICS = auto()  # citation_count, reference_count
    CLASSIFICATION = auto()  # mesh_terms, keywords, subjects
    URLS = auto()  # url, pdf_url, landing_page
    OTHER = auto()  # Everything else


# Mapping of field patterns to semantic groups
# Patterns are matched case-insensitively
PUBLICATION_FIELD_GROUPS: Final[dict[str, SemanticGroup]] = {
    # System fields (exact match)
    "entity_id": SemanticGroup.SYSTEM,
    "content_hash": SemanticGroup.SYSTEM,
    "_run_id": SemanticGroup.SYSTEM,
    "_ingestion_ts": SemanticGroup.SYSTEM,
    "_run_type": SemanticGroup.SYSTEM,
    "_source_file": SemanticGroup.SYSTEM,
    "_dq_score": SemanticGroup.SYSTEM,
    "_dq_flags": SemanticGroup.SYSTEM,
    "_lineage": SemanticGroup.SYSTEM,
    "_sources": SemanticGroup.SYSTEM,
    # Identifiers
    "document_chembl_id": SemanticGroup.IDENTIFIERS,
    "publication_id": SemanticGroup.IDENTIFIERS,
    "chembl_id": SemanticGroup.IDENTIFIERS,
    "doi": SemanticGroup.IDENTIFIERS,
    "pmid": SemanticGroup.IDENTIFIERS,
    "pmc_id": SemanticGroup.IDENTIFIERS,
    "pmcid": SemanticGroup.IDENTIFIERS,
    "pubmed_id": SemanticGroup.IDENTIFIERS,
    "openalex_id": SemanticGroup.IDENTIFIERS,
    "semantic_scholar_id": SemanticGroup.IDENTIFIERS,
    "crossref_id": SemanticGroup.IDENTIFIERS,
    "issn": SemanticGroup.IDENTIFIERS,
    "isbn": SemanticGroup.IDENTIFIERS,
    # Title
    "title": SemanticGroup.TITLE,
    "original_title": SemanticGroup.TITLE,
    "translated_title": SemanticGroup.TITLE,
    "subtitle": SemanticGroup.TITLE,
    # Abstract
    "abstract": SemanticGroup.ABSTRACT,
    "summary": SemanticGroup.ABSTRACT,
    "description": SemanticGroup.ABSTRACT,
    # Authors
    "authors": SemanticGroup.AUTHORS,
    "author": SemanticGroup.AUTHORS,
    "first_author": SemanticGroup.AUTHORS,
    "last_author": SemanticGroup.AUTHORS,
    "corresponding_author": SemanticGroup.AUTHORS,
    "author_count": SemanticGroup.AUTHORS,
    "affiliations": SemanticGroup.AUTHORS,
    "institutions": SemanticGroup.AUTHORS,
    # Journal/Source
    "journal": SemanticGroup.JOURNAL,
    "journal_title": SemanticGroup.JOURNAL,
    "source": SemanticGroup.JOURNAL,
    "publisher": SemanticGroup.JOURNAL,
    "volume": SemanticGroup.JOURNAL,
    "issue": SemanticGroup.JOURNAL,
    "pages": SemanticGroup.JOURNAL,
    "first_page": SemanticGroup.JOURNAL,
    "last_page": SemanticGroup.JOURNAL,
    # Dates
    "publication_date": SemanticGroup.DATES,
    "pub_date": SemanticGroup.DATES,
    "year": SemanticGroup.DATES,
    "publication_year": SemanticGroup.DATES,
    "created_at": SemanticGroup.DATES,
    "updated_at": SemanticGroup.DATES,
    "indexed_at": SemanticGroup.DATES,
    "deposited_at": SemanticGroup.DATES,
    # Metrics
    "citation_count": SemanticGroup.METRICS,
    "citations": SemanticGroup.METRICS,
    "cited_by_count": SemanticGroup.METRICS,
    "reference_count": SemanticGroup.METRICS,
    "references": SemanticGroup.METRICS,
    "impact_factor": SemanticGroup.METRICS,
    "h_index": SemanticGroup.METRICS,
    "altmetric_score": SemanticGroup.METRICS,
    # Classification
    "mesh_terms": SemanticGroup.CLASSIFICATION,
    "mesh_headings": SemanticGroup.CLASSIFICATION,
    "keywords": SemanticGroup.CLASSIFICATION,
    "subjects": SemanticGroup.CLASSIFICATION,
    "categories": SemanticGroup.CLASSIFICATION,
    "topics": SemanticGroup.CLASSIFICATION,
    "concepts": SemanticGroup.CLASSIFICATION,
    "publication_type": SemanticGroup.CLASSIFICATION,
    "document_type": SemanticGroup.CLASSIFICATION,
    # URLs
    "url": SemanticGroup.URLS,
    "pdf_url": SemanticGroup.URLS,
    "landing_page": SemanticGroup.URLS,
    "landing_page_url": SemanticGroup.URLS,
    "fulltext_url": SemanticGroup.URLS,
    "open_access_url": SemanticGroup.URLS,
}


@dataclass(frozen=True)
class ColumnOrderConfig:
    """Configuration for column ordering.

    Attributes:
        field_groups: Mapping of field names to semantic groups.
        provider_priority: Order of providers within same semantic group.
            First provider's columns appear first.
    """

    field_groups: dict[str, SemanticGroup] = field(
        default_factory=lambda: dict(PUBLICATION_FIELD_GROUPS)
    )
    provider_priority: tuple[str, ...] = (
        "chembl",
        "crossref",
        "pubmed",
        "openalex",
        "semantic_scholar",
    )

    def get_group(self, column: str) -> SemanticGroup:
        """Get semantic group for a column.

        Handles both qualified (provider.entity.field) and
        unqualified (field) column names.

        Args:
            column: Column name.

        Returns:
            Semantic group for the column.
        """
        # Handle system columns (start with _)
        if column.startswith("_"):
            return self.field_groups.get(column, SemanticGroup.SYSTEM)

        # Extract and normalize field name
        field_lower = self._extract_field(column).lower()

        # Try exact match first, then fallback to OTHER
        return self.field_groups.get(field_lower, SemanticGroup.OTHER)

    def get_provider_rank(self, column: str) -> int:
        """Get provider rank for ordering within semantic group.

        Args:
            column: Column name (qualified or unqualified).

        Returns:
            Provider rank (lower = higher priority).
            Returns 999 for unknown providers.
        """
        # Extract provider from qualified name
        parts = column.split(".")
        if len(parts) == 3:
            provider = parts[0].lower()
            try:
                return self.provider_priority.index(provider)
            except ValueError:
                return 999

        # Unqualified columns get highest priority (seed)
        return -1

    def _extract_field(self, column: str) -> str:
        """Extract field name from column."""
        parts = column.split(".")
        if len(parts) == 3:
            return parts[2]
        return column


# Default configuration instance
DEFAULT_COLUMN_ORDER: Final[ColumnOrderConfig] = ColumnOrderConfig()
