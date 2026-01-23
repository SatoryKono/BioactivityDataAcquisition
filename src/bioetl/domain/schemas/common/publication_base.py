"""Base schema for all publication entities across providers.

Aligned with RULES.md v5.10 and Publication Schema Unification spec.
Provides unified field set for cross-provider publication analysis.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.validation import (
    DOI_REGEX_PATTERN,
    MAX_PUBLICATION_YEAR,
    MIN_PUBLICATION_YEAR,
)

# Lookup method values (used by all publication providers)
LOOKUP_METHODS = ["direct", "doi", "pmid", "title_fallback", "title_only", "unknown"]

# Open Access status values (normalized to lowercase for cross-provider consistency)
OA_STATUS_VALUES = ["gold", "green", "hybrid", "bronze", "closed"]


class PublicationBaseSchema(ETLRecordSchema):
    """Base schema with common fields for all publication entities.

    Provider-specific schemas inherit from this and add their own fields.
    This unified schema ensures cross-provider analysis compatibility.

    Field Categories:
    - Cross-reference IDs: pmid, doi, pmc_id
    - Core content: title, abstract, authors
    - Publication metadata: journal, year, publication_date, doc_type, language
    - Metrics: citation_count
    - Open Access: is_oa
    - Lookup tracking: _lookup_method, _original_id
    - System: _source (data source identifier)
    """

    # === Cross-reference IDs (common to all providers) ===
    # Note: PubMed overrides pmid to be int type instead of str
    pmid: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^\d+$",
        description="PubMed ID (numeric string)",
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

    # === Publication metadata (common to all providers) ===
    journal: Series[str] = pa.Field(
        nullable=True,
        description="Journal name",
    )
    year: Series[int] = pa.Field(
        nullable=True,
        ge=MIN_PUBLICATION_YEAR,
        le=MAX_PUBLICATION_YEAR,
        description="Publication year",
    )
    publication_date: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{2}-\d{2}$",
        description="Publication date (YYYY-MM-DD)",
    )
    doc_type: Series[str] = pa.Field(
        nullable=True,
        description="Document type (PUBLICATION, PREPRINT, PATENT, etc.)",
    )
    language: Series[str] = pa.Field(
        nullable=True,
        description="Language code (ISO 639-1 or MARC)",
    )

    # === Metrics (common to all providers) ===
    # Use pd.Int64Dtype for nullable integer support
    citation_count: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of citations (provider-dependent availability)",
    )

    # === Open Access (common to all providers) ===
    is_oa: Series[bool] = pa.Field(
        nullable=True,
        description="Is Open Access (provider-dependent availability)",
    )

    # === Lookup tracking (common to all providers) ===
    # Note: alias maps Python attribute name to DataFrame column name
    lookup_method: Series[str] = pa.Field(
        alias="_lookup_method",
        nullable=True,
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
