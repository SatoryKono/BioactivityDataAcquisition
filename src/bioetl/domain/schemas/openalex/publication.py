"""Pandera schema for OpenAlex Publication entity.

Aligned with RULES.md v5.8.
Includes lookup metadata fields for DOI/title resolution tracking.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.validation import DOI_REGEX_PATTERN

# Lookup method values
LOOKUP_METHODS = ["doi", "title_fallback", "title_only", "unknown"]

# Valid OA status values
OA_STATUS_VALUES = ["gold", "green", "hybrid", "bronze", "closed"]


class OpenAlexPublicationSchema(ETLRecordSchema):
    """OpenAlex Publication validation schema for Silver layer.

    Validates publication records from OpenAlex Works API.
    Includes both core publication fields and lookup metadata
    for batch DOI resolution tracking.
    """

    # === Primary Key ===
    openalex_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^W\d+$",
        description="OpenAlex Work ID (e.g., W2148763428)",
    )

    # === Core Fields ===
    doi: Series[str] = pa.Field(
        nullable=True,
        str_matches=DOI_REGEX_PATTERN,
        description="Digital Object Identifier",
    )

    title: Series[str] = pa.Field(
        nullable=True,
        description="Publication title",
    )

    abstract: Series[str] = pa.Field(
        nullable=True,
        description="Reconstructed abstract",
    )

    year: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        ge=1500,
        le=2100,
        description="Publication year",
    )

    publication_date: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{2}-\d{2}$",
        description="Publication date (YYYY-MM-DD)",
    )

    doc_type: Series[str] = pa.Field(
        nullable=False,
        description="Publication type (PUBLICATION, PREPRINT, etc.)",
    )

    # === Journal ===
    journal: Series[str] = pa.Field(
        nullable=True,
        description="Journal/source name",
    )

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

    # === Metrics ===
    # OpenAlex source field: cited_by_count
    # Unified BioETL field: citation_count (standardized across all providers)
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

    # === Lookup Metadata (batch DOI resolution) ===
    # Note: Using alias for underscore-prefixed column names since Pandera
    # treats underscore-prefixed attributes as private with strict='filter'
    lookup_method: Series[str] = pa.Field(
        alias="_lookup_method",
        nullable=False,
        isin=LOOKUP_METHODS,
        description="How record was resolved: doi, title_fallback, title_only",
    )

    original_doi: Series[str] = pa.Field(
        alias="_original_doi",
        nullable=True,
        description="Original DOI from input CSV (for fallback records)",
    )

    class Config:
        """Pandera configuration."""

        strict = "filter"  # Filter out columns not in schema
        coerce = True  # Coerce data types to match schema
