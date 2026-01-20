"""Pandera schema for OpenAlex Publication entity.

Aligned with RULES.md v5.10 and Publication Schema Unification spec.
Includes lookup metadata fields for DOI/title resolution tracking.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import (
    LOOKUP_METHODS,
    OA_STATUS_VALUES,
    PublicationBaseSchema,
)
from bioetl.domain.validation import DOI_REGEX_PATTERN

# Re-export for backwards compatibility
__all__ = [
    "DOI_REGEX_PATTERN",
    "LOOKUP_METHODS",
    "OA_STATUS_VALUES",
    "OpenAlexPublicationSchema",
]


class OpenAlexPublicationSchema(PublicationBaseSchema):
    """OpenAlex Publication validation schema for Silver layer.

    Validates publication records from OpenAlex Works API.
    Inherits common fields from PublicationBaseSchema:
    - Cross-references: pmid, doi, pmc_id
    - Core content: title, abstract, authors
    - Metadata: journal, year (overridden), publication_date, doc_type (overridden), language
    - Metrics: citation_count (overridden for nullable int)
    - Open Access: is_oa
    - Lookup tracking: lookup_method (overridden), original_id, source (overridden)
    """

    # === Primary Key (OpenAlex-specific) ===
    openalex_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^W\d+$",
        description="OpenAlex Work ID (e.g., W2148763428)",
    )

    # === Override lookup_method to be non-nullable ===
    lookup_method: Series[str] = pa.Field(
        alias="_lookup_method",
        nullable=False,
        isin=LOOKUP_METHODS,
        description="How record was resolved: doi, title_fallback, title_only",
    )

    # === Override year with pd.Int64Dtype for nullable int ===
    year: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=1800,
        le=2100,
        description="Publication year (1800-2100).",
    )

    # === Override doc_type to be non-nullable ===
    doc_type: Series[str] = pa.Field(
        nullable=False,
        description="Publication type (PUBLICATION, PREPRINT, etc.)",
    )

    # === Override citation_count with pd.Int64Dtype for nullable int ===
    citation_count: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of citations (from OpenAlex cited_by_count).",
    )

    # === Override source to be non-nullable ===
    source: Series[str] = pa.Field(
        nullable=False,
        description="Data source identifier",
    )

    # === Provider-specific Fields ===
    issn: Series[str] = pa.Field(
        nullable=True,
        description="ISSN-L",
    )

    publisher: Series[str] = pa.Field(
        nullable=True,
        description="Publisher name",
    )

    oa_status: Series[str] = pa.Field(
        nullable=True,
        isin=OA_STATUS_VALUES,
        description="OA status (gold, green, hybrid, bronze, closed)",
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Allow missing columns and extra columns
        coerce = True  # Coerce data types to match schema
