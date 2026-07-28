# pyright: reportIncompatibleVariableOverride=false
# Pandera/ETL nested Config override pattern (PD2-7).
"""Base schema for all publication entities across providers.

Aligned with RULES.md v5.24 and Publication Schema Unification spec.
Provides unified field set for cross-provider publication analysis.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import ISSN_PATTERN, OA_STATUS_VALUES
from bioetl.domain.validation import (
    DOI_REGEX_PATTERN,
    MAX_PUBLICATION_YEAR,
    MIN_PUBLICATION_YEAR,
)

__all__ = [
    "LOOKUP_METHODS",
    "OA_STATUS_VALUES",
    "PublicationBaseSchema",
]

# Lookup method values (used by all publication providers)
LOOKUP_METHODS = ["direct", "doi", "pmid", "title_fallback", "title_only", "unknown"]


class PublicationBaseSchema(ETLRecordSchema):
    """Base schema with common fields for all publication entities.

    Provider-specific schemas inherit from this and add their own fields.
    This unified schema ensures cross-provider analysis compatibility.

    Field Categories (unified field names):
    - Cross-reference IDs: pmid, doi, pmc_id
    - Core content: title, abstract, authors, affiliation_list
    - Publication metadata: journal, publication_year, publication_date, publication_type, language
    - Pagination: page_first, page_last
    - Metrics: citations_received, citations_made
    - Open Access: is_oa
    - Lookup tracking: _lookup_method, _original_id
    - System: _source (data source identifier)

    Note: Old field names (year, doc_type, citation_count, first_page, last_page)
    have been replaced with unified names for cross-provider consistency.
    """

    # === Cross-reference IDs (common to all providers) ===
    # Note: PubMed overrides pubmed_id to be int type instead of str
    pmid: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^[1-9]\d{0,9}$",
        description="PubMed ID (positive numeric string < 10^10)",
    )
    doi: Series[str] = pa.Field(
        nullable=True,
        str_matches=DOI_REGEX_PATTERN,
        description="Digital Object Identifier (lowercase)",
    )
    pmc_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^PMC\d+$",
        description="PubMed Central ID",
    )

    # === Core content (common to all providers) ===
    title: Series[str] = pa.Field(nullable=True, description="Publication title")
    abstract: Series[str] = pa.Field(nullable=True, description="Publication abstract")
    authors: Series[str] = pa.Field(
        nullable=True,
        description="JSON array of author names (PII hashed)",
    )
    affiliation_list: Series[str] = pa.Field(
        nullable=True,
        description="JSON array of unique affiliations (unified field name)",
    )
    author_orcids: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of author ORCID identifiers (format: 0000-0000-0000-000X)",
    )
    author_keys: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited short author keys (Surname_F format)",
    )

    # === Publication metadata (common to all providers) ===
    journal: Series[str] = pa.Field(
        nullable=True,
        description="Journal name",
    )
    issn: Series[str] = pa.Field(
        nullable=True,
        str_matches=ISSN_PATTERN,
        description="Primary ISSN (format: NNNN-NNNN)",
    )
    issn_list: Series[str] = pa.Field(
        nullable=True,
        description="Canonical JSON array of ISSN values",
    )
    publication_year: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=MIN_PUBLICATION_YEAR,
        le=MAX_PUBLICATION_YEAR,
        description="Publication year (unified field name)",
    )
    publication_date: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{2}-\d{2}$",
        description="Publication date (YYYY-MM-DD)",
    )
    publication_type: Series[str] = pa.Field(
        nullable=True,
        description="Raw provider type string (preserved for forensic/debug)",
    )
    publication_type_unified: Series[str] = pa.Field(
        nullable=True,
        description="Unified type Level 3: 'Journal Article', 'Preprint', 'Clinical Trial', etc.",
    )
    publication_subclass: Series[str] = pa.Field(
        nullable=True,
        description="Subclass Level 2: 'Original Experimental Data', 'Reviews & Syntheses', etc.",
    )
    publication_class: Series[str] = pa.Field(
        nullable=True,
        isin=["EXP", "REV", "PEER", "PUBLICATION"],
        description=(
            "Class Level 1: EXP (experimental), REV (reviews/secondary), "
            "PEER (peer review), or provider-preserved PUBLICATION."
        ),
    )
    language: Series[str] = pa.Field(
        nullable=True,
        str_length={"min_value": 2, "max_value": 3},
        description="Language code (ISO 639-1 or MARC)",
    )

    # === Pagination (unified field names) ===
    page_first: Series[str] = pa.Field(
        nullable=True,
        description="First page number (unified field name)",
    )
    page_last: Series[str] = pa.Field(
        nullable=True,
        description="Last page number (unified field name)",
    )

    # === Metrics (unified field names) ===
    # Use pd.Int64Dtype for nullable integer support
    citations_received: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of citations TO this publication (unified field name)",
    )
    citations_made: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of references FROM this publication (unified field name)",
    )

    # === Open Access (common to all providers) ===
    is_oa: Series[pd.BooleanDtype] = pa.Field(
        nullable=True,
        description="Is Open Access (provider-dependent availability)",
    )

    # === Lookup tracking (common to all providers) ===
    # Note: alias maps Python attribute name to DataFrame column name
    lookup_method: Series[str] = pa.Field(
        alias="_lookup_method",
        nullable=False,
        isin=LOOKUP_METHODS,
        description="How record was resolved: direct, doi, pmid, title_fallback, title_only",
    )
    original_id: Series[str] = pa.Field(
        alias="_original_id",
        nullable=True,
        description="Original identifier from input (for fallback records)",
    )

    # === System field (per SYSTEM_FIELDS_PREFIX) ===
    _source: Series[str] = pa.Field(
        nullable=True,
        description="Data source identifier (e.g., chembl, pubmed, crossref, openalex)",
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Allow extra columns
        ordered = False
        coerce = True
