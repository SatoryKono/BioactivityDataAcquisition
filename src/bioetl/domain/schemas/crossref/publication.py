"""Pandera schema for CrossRef Publication (enriched) entity.

Used for Silver layer validation of publications enriched via CrossRef API.
Aligned with RULES.md v5.10 and Publication Schema Unification spec.
"""

from __future__ import annotations

import json
import re
from typing import cast

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import (
    LOOKUP_METHODS,
    PublicationBaseSchema,
)
from bioetl.domain.schemas.constants import ISSN_PATTERN, ORCID_PATTERN
from bioetl.domain.validation import DOI_REGEX_PATTERN

# Re-export for backwards compatibility
__all__ = ["DOI_REGEX_PATTERN", "LOOKUP_METHODS", "PublicationEnrichedSchema"]

# === Fixed Value Constants ===
DOCUMENT_TYPES = ["PUBLICATION", "PREPRINT"]


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

    # === Primary Key (override doi to be non-nullable) ===
    doi: Series[str] = pa.Field(
        nullable=False,
        str_matches=DOI_REGEX_PATTERN,
        description="Digital Object Identifier (normalized: lowercase, stripped)",
    )

    # === Provider-specific Fields ===
    issn: Series[str] = pa.Field(
        nullable=True,
        str_matches=ISSN_PATTERN,
        description="Primary ISSN (first from ISSN array)",
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
    content_domain_domains: Series[object] = pa.Field(
        nullable=True,
        description="Content domain domains (list of strings)",
    )
    content_domain_crossmark_restriction: Series[bool] = pa.Field(
        nullable=True,
        coerce=True,
        description="Crossmark restriction flag",
    )

    # === Alternative Identifiers ===
    alternative_id: Series[object] = pa.Field(
        nullable=True,
        description="Alternative IDs (publisher-specific, e.g., PII)",
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
        description="Print ISSN (format: XXXX-XXXX)",
    )
    issn_electronic: Series[str] = pa.Field(
        nullable=True,
        str_matches=ISSN_PATTERN,
        description="Electronic ISSN (format: XXXX-XXXX)",
    )

    # === Author ORCID Identifiers ===
    author_orcid_list: Series[str] = pa.Field(
        nullable=True,
        description="JSON array of author ORCID identifiers (format: 0000-0000-0000-000X)",
    )

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

    @pa.check("author_orcid_list", name="orcid_format")
    def _check_author_orcid_list(cls, series: Series[str]) -> Series[bool]:
        """Validate ORCID format in JSON array elements."""
        _pattern = re.compile(ORCID_PATTERN)

        def _valid(val: object) -> bool:
            if pd.isna(val):
                return True
            try:
                items = json.loads(str(val))
                return all(
                    not item or _pattern.match(item) is not None for item in items
                )
            except (json.JSONDecodeError, TypeError):
                return False

        return cast("Series[bool]", series.apply(_valid))

    class Config:
        """Pandera configuration."""

        strict = False  # Allow missing columns and extra columns
        ordered = False  # Changed to False for inheritance compatibility
        coerce = True
        name = "PublicationEnrichedSchema"
        description = "CrossRef-enriched Publication Silver layer validation"
