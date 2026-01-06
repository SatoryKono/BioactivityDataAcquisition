"""Pandera schema for OpenAlex Publication entity.

Aligned with RULES.md v5.8.
Includes lookup metadata fields for DOI/title resolution tracking.
"""

from __future__ import annotations

from typing import cast

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

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
        description="OpenAlex Work ID (e.g., W2148763428)",
    )

    # NOTE: Do not add @classmethod - Pandera requires @pa.check to be the outermost decorator
    @pa.check("openalex_id", name="openalex_id_format")
    def _check_openalex_id(cls, series: Series[str]) -> Series[bool]:
        """Validate OpenAlex ID format."""
        return cast("Series[bool]", series.str.match(r"^W\d+$"))

    # === Core Fields ===
    doi: Series[str] = pa.Field(
        nullable=True,
        description="Digital Object Identifier",
    )

    @pa.check("doi", name="doi_format")
    def _check_doi(cls, series: Series[str]) -> Series[bool]:
        """Validate DOI format."""
        return cast(
            "Series[bool]", series.isna() | series.str.match(r"^10\.\d{4,}/.*$")
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
        description="Publication year",
    )

    @pa.check("year", name="year_range")
    def _check_year(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate year range."""
        return cast(
            "Series[bool]", series.isna() | ((series >= 1500) & (series <= 2100))
        )

    publication_date: Series[str] = pa.Field(
        nullable=True,
        description="Publication date (YYYY-MM-DD)",
    )

    @pa.check("publication_date", name="publication_date_format")
    def _check_publication_date(cls, series: Series[str]) -> Series[bool]:
        """Validate publication date format."""
        return cast(
            "Series[bool]", series.isna() | series.str.match(r"^\d{4}-\d{2}-\d{2}$")
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
        description="OA status",
    )

    @pa.check("oa_status", name="oa_status_values")
    def _check_oa_status(cls, series: Series[str]) -> Series[bool]:
        """Validate OA status values."""
        return cast("Series[bool]", series.isna() | series.isin(OA_STATUS_VALUES))

    # === Metrics ===
    cited_by_count: Series[pd.Int64Dtype] = pa.Field(
        nullable=True,
        description="Citation count",
    )

    @pa.check("cited_by_count", name="cited_by_count_non_negative")
    def _check_cited_by_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate citation count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

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
        description="How record was resolved: doi, title_fallback, title_only",
    )

    @pa.check("_lookup_method", name="lookup_method_values")
    def _check_lookup_method(cls, series: Series[str]) -> Series[bool]:
        """Validate lookup method values."""
        return cast("Series[bool]", series.isin(LOOKUP_METHODS))

    original_doi: Series[str] = pa.Field(
        alias="_original_doi",
        nullable=True,
        description="Original DOI from input CSV (for fallback records)",
    )

    class Config:
        """Pandera configuration."""

        strict = "filter"  # Filter out columns not in schema
        coerce = True  # Coerce data types to match schema
