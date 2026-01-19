"""Pandera schema for OpenAlex Publication entity.

Aligned with RULES.md v5.10.
Includes lookup metadata fields for DOI/title resolution tracking.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import (
    LOOKUP_METHODS,
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

# Valid OA status values
OA_STATUS_VALUES = ["gold", "green", "hybrid", "bronze", "closed"]


class OpenAlexPublicationSchema(PublicationBaseSchema):
    """OpenAlex Publication validation schema for Silver layer.

    Validates publication records from OpenAlex Works API.
    Includes both core publication fields and lookup metadata
    for batch DOI resolution tracking.
    """

    # === Lookup metadata (OpenAlex-specific) ===
    lookup_method: Series[str] = pa.Field(
        alias="_lookup_method",
        nullable=False,
        isin=LOOKUP_METHODS,
        description="How record was resolved: doi, title_fallback, title_only",
    )
    original_id: Series[str] = pa.Field(
        alias="_original_id",
        nullable=True,
        description="Original identifier from input (for fallback records)",
    )

    # === Primary Key ===
    openalex_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^W\d+$",
        description="OpenAlex Work ID (e.g., W2148763428)",
    )

    # === Override year with pd.Int64Dtype for nullable int ===
    year: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=1800,
        le=2100,
        description="Publication year (1800-2100).",
    )

    # === Publication date ===
    publication_date: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{2}-\d{2}$",
        description="Publication date (YYYY-MM-DD)",
    )

    # === Override doc_type to be non-nullable ===
    doc_type: Series[str] = pa.Field(
        nullable=False,
        description="Publication type (PUBLICATION, PREPRINT, etc.)",
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

    # === Open Access ===
    is_oa: Series[bool] = pa.Field(
        nullable=True,
        description="Is Open Access",
    )

    oa_status: Series[str] = pa.Field(
        nullable=True,
        isin=OA_STATUS_VALUES,
        description="OA status",
    )

    # === Override citation_count with pd.Int64Dtype for nullable int ===
    citation_count: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of citations (from OpenAlex cited_by_count).",
    )

    # === Metadata ===
    language: Series[str] = pa.Field(
        nullable=True,
        description="Language code",
    )

    source: Series[str] = pa.Field(
        nullable=False,
        description="Data source identifier",
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Allow missing columns and extra columns
        coerce = True  # Coerce data types to match schema
