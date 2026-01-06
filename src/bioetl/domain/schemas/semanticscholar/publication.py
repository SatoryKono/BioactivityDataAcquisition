# src/bioetl/domain/schemas/semanticscholar/publication.py
"""Pandera schema for Semantic Scholar Publication entity.

Aligned with RULES.md v5.8.
Includes lookup metadata fields for DOI/title resolution tracking.
"""

from __future__ import annotations

from typing import cast

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

# Lookup method values for batch DOI resolution
LOOKUP_METHODS = ["doi", "title_fallback", "title_only", "unknown"]

# Open Access status values (from S2 API)
OA_STATUS_VALUES = ["GREEN", "GOLD", "HYBRID", "BRONZE"]


class SemanticScholarPublicationSchema(ETLRecordSchema):
    """Semantic Scholar Publication validation schema for Silver layer.

    Validates publication records from Semantic Scholar Academic Graph API.
    Includes lookup metadata for tracking DOI vs title resolution.
    """

    # === Primary Key ===
    paper_id: Series[str] = pa.Field(
        nullable=False,
        description="Semantic Scholar Paper ID (40-char hex)",
    )

    @pa.check("paper_id", name="paper_id_format")
    def _check_paper_id(cls, series: Series[str]) -> Series[bool]:  # noqa: N805
        """Validate Semantic Scholar paper ID format."""
        return cast("Series[bool]", series.str.match(r"^[a-f0-9]{40}$"))

    # === External Identifiers ===
    doi: Series[str] = pa.Field(
        nullable=True,
        description="Digital Object Identifier",
    )

    @pa.check("doi", name="doi_format")
    def _check_doi(cls, series: Series[str]) -> Series[bool]:  # noqa: N805
        """Validate DOI format."""
<<<<<<< claude/run-tests-debug-Yo6uX
        return cast(
            "Series[bool]", series.isna() | series.str.match(r"^10\.\d{4,}/.*$")
        )
=======
        return cast("Series[bool]", series.isna() | series.str.match(r"^10\.\d{4,}/.*$"))
>>>>>>> main

    pmid: Series[str] = pa.Field(
        nullable=True,
        description="PubMed ID",
    )

    @pa.check("pmid", name="pmid_format")
    def _check_pmid(cls, series: Series[str]) -> Series[bool]:  # noqa: N805
        """Validate PMID format."""
        return cast("Series[bool]", series.isna() | series.str.match(r"^\d+$"))

    pmcid: Series[str] = pa.Field(
        nullable=True,
        description="PubMed Central ID",
    )

    @pa.check("pmcid", name="pmcid_format")
    def _check_pmcid(cls, series: Series[str]) -> Series[bool]:  # noqa: N805
        """Validate PMCID format."""
        return cast("Series[bool]", series.isna() | series.str.match(r"^PMC\d+$"))

    arxiv_id: Series[str] = pa.Field(
        nullable=True,
        description="ArXiv ID",
    )

    corpus_id: Series[int] = pa.Field(
        nullable=True,
        description="S2 Corpus ID",
    )

    @pa.check("corpus_id", name="corpus_id_non_negative")
    def _check_corpus_id(cls, series: Series[int]) -> Series[bool]:  # noqa: N805
        """Validate corpus ID is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    # === Core Fields ===
    title: Series[str] = pa.Field(
        nullable=True,
        description="Publication title",
    )

    abstract: Series[str] = pa.Field(
        nullable=True,
        description="Abstract text",
    )

    tldr: Series[str] = pa.Field(
        nullable=True,
        description="AI-generated summary (TLDR)",
    )

    year: Series[int] = pa.Field(
        nullable=True,
        description="Publication year",
    )

    @pa.check("year", name="year_range")
    def _check_year(cls, series: Series[int]) -> Series[bool]:  # noqa: N805
        """Validate year range."""
<<<<<<< claude/run-tests-debug-Yo6uX
        return cast(
            "Series[bool]", series.isna() | ((series >= 1500) & (series <= 2100))
        )
=======
        return cast("Series[bool]", series.isna() | ((series >= 1500) & (series <= 2100)))
>>>>>>> main

    publication_date: Series[str] = pa.Field(
        nullable=True,
        description="Publication date (YYYY-MM-DD)",
    )

    @pa.check("publication_date", name="publication_date_format")
    def _check_publication_date(cls, series: Series[str]) -> Series[bool]:  # noqa: N805
        """Validate publication date format."""
<<<<<<< claude/run-tests-debug-Yo6uX
        return cast(
            "Series[bool]", series.isna() | series.str.match(r"^\d{4}-\d{2}-\d{2}$")
        )
=======
        return cast("Series[bool]", series.isna() | series.str.match(r"^\d{4}-\d{2}-\d{2}$"))
>>>>>>> main

    # === Journal/Venue ===
    journal: Series[str] = pa.Field(
        nullable=True,
        description="Journal name",
    )

    volume: Series[str] = pa.Field(
        nullable=True,
        description="Journal volume",
    )

    pages: Series[str] = pa.Field(
        nullable=True,
        description="Page range",
    )

    venue: Series[str] = pa.Field(
        nullable=True,
        description="Publication venue",
    )

    # === Metrics ===
    citation_count: Series[int] = pa.Field(
        nullable=True,
        description="Number of citations",
    )

    @pa.check("citation_count", name="citation_count_non_negative")
    def _check_citation_count(cls, series: Series[int]) -> Series[bool]:  # noqa: N805
        """Validate citation count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    reference_count: Series[int] = pa.Field(
        nullable=True,
        description="Number of references",
    )

    @pa.check("reference_count", name="reference_count_non_negative")
    def _check_reference_count(cls, series: Series[int]) -> Series[bool]:  # noqa: N805
        """Validate reference count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    # === Open Access ===
    is_open_access: Series[bool] = pa.Field(
        nullable=True,
        description="Is Open Access",
    )

    open_access_url: Series[str] = pa.Field(
        nullable=True,
        description="Direct link to OA PDF",
    )

    open_access_status: Series[str] = pa.Field(
        nullable=True,
        description="OA status (GREEN, GOLD, HYBRID, BRONZE)",
    )

    @pa.check("open_access_status", name="open_access_status_values")
    def _check_open_access_status(cls, series: Series[str]) -> Series[bool]:  # noqa: N805
        """Validate OA status values."""
        return cast("Series[bool]", series.isna() | series.isin(OA_STATUS_VALUES))

    # === Classification ===
    fields_of_study: Series[str] = pa.Field(
        nullable=True,
        description="Fields of study (JSON array)",
    )

    publication_types: Series[str] = pa.Field(
        nullable=True,
        description="Publication types (JSON array)",
    )

    # === Authors (hashed for PII compliance) ===
    authors: Series[str] = pa.Field(
        nullable=True,
        description="Author names (JSON array, optionally hashed)",
    )

    # === Source Tracking ===
    source: Series[str] = pa.Field(
        nullable=False,
        description="Data source identifier",
    )

    @pa.check("source", name="source_values")
    def _check_source(cls, series: Series[str]) -> Series[bool]:
        """Validate source values."""
        return cast("Series[bool]", series.isin(["semanticscholar"]))

    # === Lookup Metadata (batch DOI resolution) ===
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
        name = "SemanticScholarPublicationSchema"
        description = "Semantic Scholar Publication Silver layer validation"
