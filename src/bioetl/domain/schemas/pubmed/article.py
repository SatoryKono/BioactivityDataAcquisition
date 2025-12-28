"""Pandera schema for PubMed Article entity.

Aligned with RULES.md v5.0 and MEDLINE DTD.
Source: https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_230101.dtd
"""
from __future__ import annotations

from datetime import date
from typing import Optional

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
    pmid: Series[int] = pa.Field(
        nullable=False,
        ge=1,
        description="PubMed ID (PK)"
    )

    # === External Identifiers ===
    doi: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_matches=r"^10\.\d{4,}/.+$",
        description="Digital Object Identifier"
    )
    pmc_id: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_matches=r"^PMC\d+$",
        description="PubMed Central ID"
    )

    # === Article Content ===
    title: Series[str] = pa.Field(
        nullable=False,
        str_length={"min_value": 1},
        description="Article title (required)"
    )
    abstract: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Abstract text (may be structured)"
    )
    abstract_structured: Optional[Series[bool]] = pa.Field(
        nullable=True,
        description="Whether abstract has NLM sections"
    )
    vernacular_title: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Original non-English title"
    )
    language: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_length={"min_value": 2, "max_value": 3},
        description="MARC language code (e.g., 'eng')"
    )

    # === Journal Information ===
    journal_title: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Full journal name"
    )
    journal_iso_abbrev: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="ISO journal abbreviation"
    )
    journal_issn: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_matches=r"^\d{4}-\d{3}[\dX]$",
        description="ISSN (print or electronic)"
    )
    journal_issn_type: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=ISSN_TYPES,
        description="ISSN type"
    )
    nlm_unique_id: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="NLM catalog ID"
    )
    country: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Journal country of publication"
    )

    # === Publication Details ===
    volume: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Journal volume"
    )
    issue: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Journal issue"
    )
    medline_pgn: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Page numbers (MEDLINE format)"
    )
    pub_year: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=1800,
        le=2100,
        description="Publication year"
    )
    pub_month: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=1,
        le=12,
        description="Publication month"
    )
    pub_day: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=1,
        le=31,
        description="Publication day"
    )
    publication_status: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=PUBLICATION_STATUSES,
        description="Publication status"
    )
    publication_type_list: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="JSON array of publication types"
    )

    # === Dates ===
    date_completed: Optional[Series[date]] = pa.Field(
        nullable=True,
        description="MEDLINE processing completion date"
    )
    date_revised: Optional[Series[date]] = pa.Field(
        nullable=True,
        description="Record revision date"
    )

    # === Metadata ===
    citation_subset: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Citation subset codes (e.g., 'AIM')"
    )

    # === Counts (denormalized for query efficiency) ===
    author_count: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of authors"
    )
    mesh_heading_count: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of MeSH headings"
    )
    keyword_count: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of keywords"
    )
    grant_count: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of grants"
    )
    reference_count: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of references"
    )
    chemical_count: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=0,
        description="Number of chemicals"
    )

    class Config:
        """Pandera configuration."""
        strict = True
        ordered = True
        coerce = True
        name = "ArticleSchema"
        description = "PubMed Article Silver layer validation"
