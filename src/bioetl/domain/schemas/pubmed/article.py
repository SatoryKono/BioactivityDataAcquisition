"""Pandera schema for PubMed Article entity.

Aligned with RULES.md v5.0 and MEDLINE DTD.
Source: https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_230101.dtd
"""

from __future__ import annotations

from datetime import date

import pandera as pa
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
    pmid: Series[int] = pa.Field(nullable=False, ge=1, description="PubMed ID (PK)")

    # === External Identifiers ===
    doi: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^10\.\d{4,}/.+$",
        description="Digital Object Identifier",
    )
    pmc_id: Series[str] | None = pa.Field(
        nullable=True, str_matches=r"^PMC\d+$", description="PubMed Central ID"
    )

    # === Article Content ===
    title: Series[str] = pa.Field(
        nullable=False,
        str_length={"min_value": 1},
        description="Article title (required)",
    )
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
        str_length={"min_value": 2, "max_value": 3},
        description="MARC language code (e.g., 'eng')",
    )

    # === Journal Information ===
    journal_title: Series[str] | None = pa.Field(
        nullable=True, description="Full journal name"
    )
    journal_iso_abbrev: Series[str] | None = pa.Field(
        nullable=True, description="ISO journal abbreviation"
    )
    journal_issn: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{3}[\dX]$",
        description="ISSN (print or electronic)",
    )
    journal_issn_type: Series[str] | None = pa.Field(
        nullable=True, isin=ISSN_TYPES, description="ISSN type"
    )
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
        nullable=True, ge=1800, le=2100, description="Publication year"
    )
    pub_month: Series[int] | None = pa.Field(
        nullable=True, ge=1, le=12, description="Publication month"
    )
    pub_day: Series[int] | None = pa.Field(
        nullable=True, ge=1, le=31, description="Publication day"
    )
    publication_status: Series[str] | None = pa.Field(
        nullable=True, isin=PUBLICATION_STATUSES, description="Publication status"
    )
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
        nullable=True, ge=0, description="Number of authors"
    )
    mesh_heading_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Number of MeSH headings"
    )
    keyword_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Number of keywords"
    )
    grant_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Number of grants"
    )
    reference_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Number of references"
    )
    chemical_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Number of chemicals"
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
        name = "ArticleSchema"
        description = "PubMed Article Silver layer validation"
