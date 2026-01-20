"""Pandera schema for PubMed Article entity.

Aligned with RULES.md v5.10 and MEDLINE DTD.
Source: https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_230101.dtd
"""

from __future__ import annotations

from datetime import date
from typing import cast

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import (
    LOOKUP_METHODS,
    PublicationBaseSchema,
)
from bioetl.domain.validation import (
    DOI_REGEX_PATTERN,
    MAX_PUBLICATION_YEAR,
    MIN_PUBLICATION_YEAR,
)

# Re-export for backwards compatibility
__all__ = ["LOOKUP_METHODS", "ArticleSchema"]

# === Fixed Value Constants ===
PUBLICATION_STATUSES = ["ppublish", "epublish", "aheadofprint"]
ISSN_TYPES = ["Print", "Electronic", "Linking"]


class ArticleSchema(PublicationBaseSchema):
    """PubMed Article validation schema for Silver layer.

    Represents a MEDLINE/PubMed citation record.
    """

    # === Primary Key (overrides base pmid: str with int) ===
    pmid: Series[int] = pa.Field(nullable=False, description="PubMed ID (PK)")

    @pa.check("pmid", name="pmid_positive")
    def _check_pmid(cls, series: Series[int]) -> Series[bool]:
        """Validate PMID is positive."""
        return cast("Series[bool]", series >= 1)

    # === External Identifiers (override doi for check method) ===
    doi: Series[str] = pa.Field(
        nullable=True,
        description="Digital Object Identifier",
    )

    @pa.check("doi", name="doi_format")
    def _check_doi(cls, series: Series[str]) -> Series[bool]:
        """Validate DOI format."""
        return cast("Series[bool]", series.isna() | series.str.match(DOI_REGEX_PATTERN))

    @pa.check("pmc_id", name="pmc_id_format")
    def _check_pmc_id(cls, series: Series[str]) -> Series[bool]:
        """Validate PMCID format."""
        return cast("Series[bool]", series.isna() | series.str.match(r"^PMC\d+$"))

    # === Article Content (override title to be non-nullable) ===
    title: Series[str] = pa.Field(
        nullable=False,
        description="Article title (required)",
    )

    @pa.check("title", name="title_not_empty")
    def _check_title(cls, series: Series[str]) -> Series[bool]:
        """Validate title is not empty."""
        return cast("Series[bool]", series.str.len() >= 1)

    abstract_structured: Series[bool] = pa.Field(
        nullable=True, description="Whether abstract has NLM sections"
    )
    vernacular_title: Series[str] = pa.Field(
        nullable=True, description="Original non-English title"
    )
    language: Series[str] = pa.Field(
        nullable=True,
        description="MARC language code (e.g., 'eng')",
    )

    @pa.check("language", name="language_length")
    def _check_language(cls, series: Series[str]) -> Series[bool]:
        """Validate language code length."""
        return cast(
            "Series[bool]",
            series.isna() | ((series.str.len() >= 2) & (series.str.len() <= 3)),
        )

    # === Journal Information (PubMed-specific) ===
    journal_title: Series[str] = pa.Field(
        nullable=True, description="Full journal name"
    )
    journal_iso_abbrev: Series[str] = pa.Field(
        nullable=True, description="ISO journal abbreviation"
    )
    journal_issn: Series[str] = pa.Field(
        nullable=True,
        description="ISSN (print or electronic)",
    )

    @pa.check("journal_issn", name="journal_issn_format")
    def _check_journal_issn(cls, series: Series[str]) -> Series[bool]:
        """Validate ISSN format."""
        return cast(
            "Series[bool]", series.isna() | series.str.match(r"^\d{4}-\d{3}[\dX]$")
        )

    journal_issn_type: Series[str] = pa.Field(nullable=True, description="ISSN type")

    @pa.check("journal_issn_type", name="journal_issn_type_values")
    def _check_journal_issn_type(cls, series: Series[str]) -> Series[bool]:
        """Validate ISSN type values."""
        return cast("Series[bool]", series.isna() | series.isin(ISSN_TYPES))

    nlm_unique_id: Series[str] = pa.Field(nullable=True, description="NLM catalog ID")
    country: Series[str] = pa.Field(
        nullable=True, description="Journal country of publication"
    )

    # === Publication Details (override year for check) ===
    medline_pgn: Series[str] = pa.Field(
        nullable=True, description="Page numbers (MEDLINE format)"
    )

    @pa.check("year", name="year_range")
    def _check_year(cls, series: Series[int]) -> Series[bool]:
        """Validate publication year range."""
        return cast(
            "Series[bool]",
            series.isna()
            | ((series >= MIN_PUBLICATION_YEAR) & (series <= MAX_PUBLICATION_YEAR)),
        )

    pub_month: Series[int] = pa.Field(nullable=True, description="Publication month")

    @pa.check("pub_month", name="pub_month_range")
    def _check_pub_month(cls, series: Series[int]) -> Series[bool]:
        """Validate publication month range."""
        return cast("Series[bool]", series.isna() | ((series >= 1) & (series <= 12)))

    pub_day: Series[int] = pa.Field(nullable=True, description="Publication day")

    @pa.check("pub_day", name="pub_day_range")
    def _check_pub_day(cls, series: Series[int]) -> Series[bool]:
        """Validate publication day range."""
        return cast("Series[bool]", series.isna() | ((series >= 1) & (series <= 31)))

    publication_status: Series[str] = pa.Field(
        nullable=True, description="Publication status"
    )

    @pa.check("publication_status", name="publication_status_values")
    def _check_publication_status(cls, series: Series[str]) -> Series[bool]:
        """Validate publication status values."""
        return cast("Series[bool]", series.isna() | series.isin(PUBLICATION_STATUSES))

    publication_type_list: Series[str] = pa.Field(
        nullable=True, description="JSON array of publication types"
    )

    # === Dates ===
    date_completed: Series[date] = pa.Field(
        nullable=True, description="MEDLINE processing completion date"
    )
    date_revised: Series[date] = pa.Field(
        nullable=True, description="Record revision date"
    )

    # === Metadata ===
    citation_subset: Series[str] = pa.Field(
        nullable=True, description="Citation subset codes (e.g., 'AIM')"
    )

    # === Counts (denormalized for query efficiency) ===
    author_count: Series[int] = pa.Field(nullable=True, description="Number of authors")

    @pa.check("author_count", name="author_count_non_negative")
    def _check_author_count(cls, series: Series[int]) -> Series[bool]:
        """Validate author count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    mesh_heading_count: Series[int] = pa.Field(
        nullable=True, description="Number of MeSH headings"
    )

    @pa.check("mesh_heading_count", name="mesh_heading_count_non_negative")
    def _check_mesh_heading_count(cls, series: Series[int]) -> Series[bool]:
        """Validate MeSH heading count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    keyword_count: Series[int] = pa.Field(
        nullable=True, description="Number of keywords"
    )

    @pa.check("keyword_count", name="keyword_count_non_negative")
    def _check_keyword_count(cls, series: Series[int]) -> Series[bool]:
        """Validate keyword count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    grant_count: Series[int] = pa.Field(nullable=True, description="Number of grants")

    @pa.check("grant_count", name="grant_count_non_negative")
    def _check_grant_count(cls, series: Series[int]) -> Series[bool]:
        """Validate grant count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    reference_count: Series[int] = pa.Field(
        nullable=True, description="Number of references"
    )

    @pa.check("reference_count", name="reference_count_non_negative")
    def _check_reference_count(cls, series: Series[int]) -> Series[bool]:
        """Validate reference count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    chemical_count: Series[int] = pa.Field(
        nullable=True, description="Number of chemicals"
    )

    @pa.check("chemical_count", name="chemical_count_non_negative")
    def _check_chemical_count(cls, series: Series[int]) -> Series[bool]:
        """Validate chemical count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    class Config:
        """Pandera configuration."""

        strict = False  # Allow missing columns and extra columns
        ordered = False  # Changed to False for inheritance compatibility
        coerce = True
        name = "ArticleSchema"
        description = "PubMed Article Silver layer validation"
