"""Pandera schema for CrossRef Publication (enriched) entity.

Used for Silver layer validation of publications enriched via CrossRef API.
Aligned with RULES.md v5.24 and Publication Schema Unification spec.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import (
    LOOKUP_METHODS,
    PublicationBaseSchema,
)
from bioetl.domain.schemas.constants import ISSN_PATTERN
from bioetl.domain.validation import DOI_REGEX_PATTERN

# Re-export for backwards compatibility
__all__ = ["DOI_REGEX_PATTERN", "LOOKUP_METHODS", "PublicationEnrichedSchema"]


class PublicationEnrichedSchema(PublicationBaseSchema):
    """CrossRef-enriched Publication validation schema for Silver layer.

    Represents publication metadata from CrossRef API with citation enrichment.
    Inherits common fields from PublicationBaseSchema:
    - Cross-references: doi (overridden to non-nullable)
    - Core content: title, abstract, authors
    - Metadata: journal, year, publication_date, language
    - Metrics: citation_count
    - Open Access: is_oa
    - Lookup tracking: _lookup_method, _original_id, source (overridden)

    Fields excluded from PyArrow/Gold schemas (not available from CrossRef API):
    - pmid: CrossRef API doesn't provide PubMed IDs
    - pmc_id: CrossRef API doesn't provide PMC IDs
    - doc_type: CrossRef uses raw 'type' field instead (journal-article, etc.)
    """

    # === Override inherited fields to allow missing (align with excluded fields) ===
    # Note: Fields are already nullable in base schema, just re-declaring here for clarity
    pmid: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^[1-9]\d{0,9}$",
        description="PubMed ID (positive numeric string < 10^10)",
    )
    pmc_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^PMC\d+$",
        description="PubMed Central ID",
    )
    abstract: Series[str] = pa.Field(
        nullable=True,
        description="Publication abstract",
    )
    affiliation_list: Series[str] = pa.Field(
        nullable=True,
        description="JSON array of unique affiliations (unified field name)",
    )

    # === Primary Key (override doi to be non-nullable) ===
    doi: Series[str] = pa.Field(
        nullable=False,
        str_matches=DOI_REGEX_PATTERN,
        description="Digital Object Identifier (normalized: lowercase, stripped)",
    )

    # === Provider-specific Fields ===
    issn: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{3}[\dX]$",
        description=(
            "Primary ISSN or provider-native serialized ISSN payload. "
            "CrossRef can surface multi-value ISSN strings here; canonical "
            "typed variants remain in issn_print / issn_electronic / issn_list."
        ),
    )
    issn_list: Series[str] = pa.Field(
        nullable=True, description="JSON array of all ISSNs"
    )
    publisher: Series[str] = pa.Field(nullable=True, description="Publisher name")

    # === Dates (CrossRef-specific) ===
    published_print: Series[str] = pa.Field(
        nullable=True, description="Print publication date (ISO format)"
    )
    published_online: Series[str] = pa.Field(
        nullable=True, description="Online publication date (ISO format)"
    )

    # === Raw CrossRef Type (replaces doc_type) ===
    publication_type: Series[str] = pa.Field(
        nullable=True,
        description="Raw CrossRef type (journal-article, book, etc.)",
    )

    # === Override _source to be non-nullable with fixed value ===
    _source: Series[str] = pa.Field(
        nullable=False, eq="crossref", description="Data source identifier"
    )

    # === Additional Metadata (CrossRef-specific) ===
    license_url: Series[str] = pa.Field(nullable=True, description="License URL")
    subject_keywords: Series[str] = pa.Field(
        nullable=True, description="JSON array of subject areas (unified field name)"
    )

    # === Content Domain ===
    content_domain_domains: Series[str] = pa.Field(
        nullable=True,
        description="Canonical JSON array of content domain domains.",
    )
    content_domain_crossmark_restriction: Series[bool] = pa.Field(
        nullable=True,
        coerce=True,
        description="Crossmark restriction flag",
    )

    # === Alternative Identifiers ===
    alternative_id: Series[str] = pa.Field(
        nullable=True,
        description="Canonical JSON array of alternative IDs (publisher-specific, e.g., PII).",
    )

    # === Canonical Publication Date ===
    published: Series[str] = pa.Field(
        nullable=True,
        description="Canonical publication date (YYYY-MM-DD)",
    )

    # === Short Container Title (unified field name) ===
    journal_name_short: Series[str] = pa.Field(
        nullable=True,
        description="Short journal/container title (unified field name)",
    )

    # === ISSN by Type ===
    issn_print: Series[str] = pa.Field(
        nullable=True,
        str_matches=ISSN_PATTERN,
        description="Print ISSN (format: NNNN-NNNN)",
    )
    issn_electronic: Series[str] = pa.Field(
        nullable=True,
        str_matches=ISSN_PATTERN,
        description="Electronic ISSN (format: NNNN-NNNN)",
    )

    # === Author ORCID Identifiers (inherited from base, kept for clarity) ===
    # author_orcids: inherited from PublicationBaseSchema

    # === Full Author Details ===
    author_details: Series[str] = pa.Field(
        nullable=True,
        description="JSON array of author objects with given, family, orcid, sequence, affiliations",
    )

    # === Bibliographic References ===
    references: Series[str] = pa.Field(
        nullable=True,
        description="JSON array of cited references with DOI, title, author, year, etc.",
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Allow missing columns and extra columns
        ordered = False  # Changed to False for inheritance compatibility
        coerce = True
        name = "PublicationEnrichedSchema"
        description = "CrossRef-enriched Publication Silver layer validation"
