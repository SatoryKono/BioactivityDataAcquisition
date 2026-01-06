"""Pandera schema for PubMed Article entity.

Aligned with RULES.md v5.0 and MEDLINE DTD.
Source: https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_230101.dtd
"""

from __future__ import annotations

from datetime import date

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

# === Fixed Value Constants ===
PUBLICATION_STATUSES = ["ppublish", "epublish", "aheadofprint"]
ISSN_TYPES = ["Print", "Electronic", "Linking"]


class ArticleSchema(ETLRecordSchema):
    """PubMed Article validation schema for Silver layer.

    Represents a MEDLINE/PubMed citation record.
    """

    # === Primary Key ===
    pmid: Series[int] = pa.Field(nullable=False, description="PubMed ID (PK)")

    @pa.check("pmid", name="pmid_positive")
    def _check_pmid(cls, series: Series[int]) -> Series[bool]:
        """Validate PMID is positive."""
        return series >= 1

    # === External Identifiers ===
    doi: Series[str] | None = pa.Field(
        nullable=True,
        description="Digital Object Identifier",
    )

    @pa.check("doi", name="doi_format")
    def _check_doi(cls, series: Series[str]) -> Series[bool]:
        """Validate DOI format."""
        return series.isna() | series.str.match(r"^10\.\d{4,}/.+$")

    pmc_id: Series[str] | None = pa.Field(
        nullable=True, description="PubMed Central ID"
    )

    @pa.check("pmc_id", name="pmc_id_format")
    def _check_pmc_id(cls, series: Series[str]) -> Series[bool]:
        """Validate PMCID format."""
        return series.isna() | series.str.match(r"^PMC\d+$")

    # === Article Content ===
    title: Series[str] = pa.Field(
        nullable=False,
        description="Article title (required)",
    )

    @pa.check("title", name="title_not_empty")
    def _check_title(cls, series: Series[str]) -> Series[bool]:
        """Validate title is not empty."""
        return series.str.len() >= 1

    abstract: Series[str] | None = pa.Field(
        nullable=True, description="Abstract text (may be structured)"
    )
    abstract_structured: Series[bool] | None = pa.Field(
        nullable=True, description="Whether abstract has NLM sections"
    )
    vernacular_title: Series[str] | None = pa.Field(
        nullable=True, description="Original non-English title"
    )
    language: Series[str] | None = pa.Field(
        nullable=True,
        description="MARC language code (e.g., 'eng')",
    )

    @pa.check("language", name="language_length")
    def _check_language(cls, series: Series[str]) -> Series[bool]:
        """Validate language code length."""
        return series.isna() | ((series.str.len() >= 2) & (series.str.len() <= 3))

    # === Journal Information ===
    journal_title: Series[str] | None = pa.Field(
        nullable=True, description="Full journal name"
    )
    journal_iso_abbrev: Series[str] | None = pa.Field(
        nullable=True, description="ISO journal abbreviation"
    )
    journal_issn: Series[str] | None = pa.Field(
        nullable=True,
        description="ISSN (print or electronic)",
    )

    @pa.check("journal_issn", name="journal_issn_format")
    def _check_journal_issn(cls, series: Series[str]) -> Series[bool]:
        """Validate ISSN format."""
        return series.isna() | series.str.match(r"^\d{4}-\d{3}[\dX]$")

    journal_issn_type: Series[str] | None = pa.Field(
        nullable=True, description="ISSN type"
    )

    @pa.check("journal_issn_type", name="journal_issn_type_values")
    def _check_journal_issn_type(cls, series: Series[str]) -> Series[bool]:
        """Validate ISSN type values."""
        return series.isna() | series.isin(ISSN_TYPES)

    nlm_unique_id: Series[str] | None = pa.Field(
        nullable=True, description="NLM catalog ID"
    )
    country: Series[str] | None = pa.Field(
        nullable=True, description="Journal country of publication"
    )

    # === Publication Details ===
    volume: Series[str] | None = pa.Field(nullable=True, description="Journal volume")
    issue: Series[str] | None = pa.Field(nullable=True, description="Journal issue")
    medline_pgn: Series[str] | None = pa.Field(
        nullable=True, description="Page numbers (MEDLINE format)"
    )
    pub_year: Series[int] | None = pa.Field(
        nullable=True, description="Publication year"
    )

    @pa.check("pub_year", name="pub_year_range")
    def _check_pub_year(cls, series: Series[int]) -> Series[bool]:
        """Validate publication year range."""
        return series.isna() | ((series >= 1800) & (series <= 2100))

    pub_month: Series[int] | None = pa.Field(
        nullable=True, description="Publication month"
    )

    @pa.check("pub_month", name="pub_month_range")
    def _check_pub_month(cls, series: Series[int]) -> Series[bool]:
        """Validate publication month range."""
        return series.isna() | ((series >= 1) & (series <= 12))

    pub_day: Series[int] | None = pa.Field(
        nullable=True, description="Publication day"
    )

    @pa.check("pub_day", name="pub_day_range")
    def _check_pub_day(cls, series: Series[int]) -> Series[bool]:
        """Validate publication day range."""
        return series.isna() | ((series >= 1) & (series <= 31))

    publication_status: Series[str] | None = pa.Field(
        nullable=True, description="Publication status"
    )

    @pa.check("publication_status", name="publication_status_values")
    def _check_publication_status(cls, series: Series[str]) -> Series[bool]:
        """Validate publication status values."""
        return series.isna() | series.isin(PUBLICATION_STATUSES)

    publication_type_list: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of publication types"
    )

    # === Dates ===
    date_completed: Series[date] | None = pa.Field(
        nullable=True, description="MEDLINE processing completion date"
    )
    date_revised: Series[date] | None = pa.Field(
        nullable=True, description="Record revision date"
    )

    # === Metadata ===
    citation_subset: Series[str] | None = pa.Field(
        nullable=True, description="Citation subset codes (e.g., 'AIM')"
    )

    # === Counts (denormalized for query efficiency) ===
    author_count: Series[int] | None = pa.Field(
        nullable=True, description="Number of authors"
    )

    @pa.check("author_count", name="author_count_non_negative")
    def _check_author_count(cls, series: Series[int]) -> Series[bool]:
        """Validate author count is non-negative."""
        return series.isna() | (series >= 0)

    mesh_heading_count: Series[int] | None = pa.Field(
        nullable=True, description="Number of MeSH headings"
    )

    @pa.check("mesh_heading_count", name="mesh_heading_count_non_negative")
    def _check_mesh_heading_count(cls, series: Series[int]) -> Series[bool]:
        """Validate MeSH heading count is non-negative."""
        return series.isna() | (series >= 0)

    keyword_count: Series[int] | None = pa.Field(
        nullable=True, description="Number of keywords"
    )

    @pa.check("keyword_count", name="keyword_count_non_negative")
    def _check_keyword_count(cls, series: Series[int]) -> Series[bool]:
        """Validate keyword count is non-negative."""
        return series.isna() | (series >= 0)

    grant_count: Series[int] | None = pa.Field(
        nullable=True, description="Number of grants"
    )

    @pa.check("grant_count", name="grant_count_non_negative")
    def _check_grant_count(cls, series: Series[int]) -> Series[bool]:
        """Validate grant count is non-negative."""
        return series.isna() | (series >= 0)

    reference_count: Series[int] | None = pa.Field(
        nullable=True, description="Number of references"
    )

    @pa.check("reference_count", name="reference_count_non_negative")
    def _check_reference_count(cls, series: Series[int]) -> Series[bool]:
        """Validate reference count is non-negative."""
        return series.isna() | (series >= 0)

    chemical_count: Series[int] | None = pa.Field(
        nullable=True, description="Number of chemicals"
    )

    @pa.check("chemical_count", name="chemical_count_non_negative")
    def _check_chemical_count(cls, series: Series[int]) -> Series[bool]:
        """Validate chemical count is non-negative."""
        return series.isna() | (series >= 0)

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
        name = "ArticleSchema"
        description = "PubMed Article Silver layer validation"
