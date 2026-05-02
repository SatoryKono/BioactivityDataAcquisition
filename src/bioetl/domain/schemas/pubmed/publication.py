"""Pandera schema for PubMed Publication entities."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, TypeVar, cast

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.common.publication_base import LOOKUP_METHODS
from bioetl.domain.schemas.constants import ISSN_PATTERN
from bioetl.domain.validation import (
    DOI_REGEX_PATTERN,
)

if TYPE_CHECKING:

    class _PublicationBaseSchema:
        """Typing-only base to avoid skipped-import degradation to Any."""

else:
    from bioetl.domain.schemas.common.publication_base import (
        PublicationBaseSchema as _PublicationBaseSchema,
    )

__all__ = ["LOOKUP_METHODS", "PubMedPublicationSchema"]

PUBLICATION_STATUSES = ["ppublish", "epublish", "aheadofprint"]
ISSN_TYPES = ["Print", "Electronic", "Linking"]

_CheckMethod = TypeVar("_CheckMethod", bound=Callable[..., object])


def _typed_check(
    *fields: str,
    **kwargs: Any,  # Any: Pandera decorator kwargs are intentionally open-ended
) -> Callable[[_CheckMethod], _CheckMethod]:
    """Typed shim around ``pa.check`` until Pandera exposes a typed decorator."""
    return cast(Callable[[_CheckMethod], _CheckMethod], pa.check(*fields, **kwargs))


class PubMedPublicationSchema(_PublicationBaseSchema):
    """PubMed Publication validation schema for Silver layer.

    Represents a MEDLINE/PubMed citation record.

    Fields excluded from PyArrow/Gold schemas (API deprecated 2026-01):
    - vernacular_title: Original non-English title (deprecated)
    - epub_date: Electronic publication date (deprecated)
    - received_date: Manuscript received date (deprecated)
    - revised_date: Manuscript revised date (deprecated)
    - accepted_date: Manuscript accepted date (deprecated)

    Fields excluded (not available from PubMed API):
    - citation_count: PubMed doesn't provide citation metrics
    - is_oa: Open Access status not available directly
    - oa_status: OA status requires external enrichment
    """

    # === Primary Key (str for cross-provider consistency) ===
    pmid: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^[1-9]\d{0,9}$",
        description="PubMed ID (PK, numeric string < 10^10)",
    )

    # === External Identifiers (override doi for check method) ===
    doi: Series[str] = pa.Field(
        nullable=True,
        str_matches=DOI_REGEX_PATTERN,
        description="Digital Object Identifier",
    )

    @_typed_check("pmc_id", name="pmc_id_format")
    def _check_pmc_id(cls, series: Series[str]) -> Series[bool]:
        """Validate PMCID format."""
        return cast(Series[bool], series.isna() | series.str.match(r"^PMC\d+$"))

    # === Additional Identifiers (for cross-referencing) ===
    pii: Series[str] = pa.Field(
        nullable=True,
        description="Publisher Item Identifier",
    )
    mid: Series[str] = pa.Field(
        nullable=True,
        description="Manuscript ID (PMC submission process)",
    )
    publisher_id: Series[str] = pa.Field(
        nullable=True,
        description="Publisher-specific article identifier",
    )

    # === Article Content (override title to be non-nullable) ===
    title: Series[str] = pa.Field(
        nullable=False,
        description="Article title (required)",
    )

    abstract_structured: Series[bool] = pa.Field(
        nullable=True, description="Whether abstract has NLM sections"
    )
    # Note: vernacular_title excluded from transformer output per design
    # language: inherited from PublicationBaseSchema (MARC codes fit str_length 2..3)

    # === Journal Information (PubMed-specific) ===
    journal: Series[str] = pa.Field(
        nullable=True, description="Full journal title (unified field name)"
    )
    journal_name_short: Series[str] = pa.Field(
        nullable=True, description="Journal abbreviation (unified field name)"
    )
    journal_iso_abbrev: Series[str] = pa.Field(
        nullable=True, description="ISO journal abbreviation"
    )
    issn: Series[str] = pa.Field(
        nullable=True,
        str_matches=ISSN_PATTERN,
        description="ISSN (print or electronic)",
    )

    journal_issn_type: Series[str] = pa.Field(nullable=True, description="ISSN type")

    @_typed_check("journal_issn_type", name="journal_issn_type_values")
    def _check_journal_issn_type(cls, series: Series[str]) -> Series[bool]:
        """Validate ISSN type values."""
        return cast(Series[bool], series.isna() | series.isin(ISSN_TYPES))

    nlm_unique_id: Series[str] = pa.Field(nullable=True, description="NLM catalog ID")
    country: Series[str] = pa.Field(
        nullable=True, description="Journal country of publication"
    )

    # === Publication Details (override year for check) ===
    medline_pgn: Series[str] = pa.Field(
        nullable=True, description="Page numbers (MEDLINE format)"
    )
    page_range: Series[str] = pa.Field(
        nullable=True, description="Page numbers (unified field name)"
    )
    pub_month: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Publication month"
    )

    @_typed_check("pub_month", name="pub_month_range")
    def _check_pub_month(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate publication month range."""
        return cast(Series[bool], series.isna() | ((series >= 1) & (series <= 12)))

    pub_day: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Publication day"
    )

    @_typed_check("pub_day", name="pub_day_range")
    def _check_pub_day(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate publication day range."""
        return cast(Series[bool], series.isna() | ((series >= 1) & (series <= 31)))

    publication_status: Series[str] = pa.Field(
        nullable=True, description="Publication status"
    )

    @_typed_check("publication_status", name="publication_status_values")
    def _check_publication_status(cls, series: Series[str]) -> Series[bool]:
        """Validate publication status values."""
        return cast(Series[bool], series.isna() | series.isin(PUBLICATION_STATUSES))

    publication_type_list: Series[str] = pa.Field(
        nullable=True, description="JSON array of publication types"
    )

    # === Dates ===
    date_completed: Series[datetime] = pa.Field(
        nullable=True, description="MEDLINE processing completion date"
    )
    date_revised: Series[datetime] = pa.Field(
        nullable=True, description="Record revision date"
    )

    # === Metadata ===
    citation_subset: Series[str] = pa.Field(
        nullable=True, description="Citation subset codes (e.g., 'AIM')"
    )

    # === Affiliation Data (enhanced for institutional analysis) ===
    affiliation_structured: Series[str] = pa.Field(
        nullable=True,
        description=(
            "JSON array of structured affiliations with identifier metadata. "
            "Each object contains: text, identifier, identifier_source, email_hash"
        ),
    )
    affiliation_structured_raw_json: Series[str] | None = pa.Field(
        nullable=True,
        description="Raw provider JSON for structured affiliations.",
    )
    affiliation_structured_canonical_json: Series[str] | None = pa.Field(
        nullable=True,
        description="Canonical JSON companion for structured affiliations.",
    )

    # === Counts (denormalized for query efficiency) ===
    author_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Number of authors"
    )

    @_typed_check("author_count", name="author_count_non_negative")
    def _check_author_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate author count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    mesh_heading_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Number of MeSH headings"
    )

    @_typed_check("mesh_heading_count", name="mesh_heading_count_non_negative")
    def _check_mesh_heading_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate MeSH heading count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    keyword_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Number of keywords"
    )

    @_typed_check("keyword_count", name="keyword_count_non_negative")
    def _check_keyword_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate keyword count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    grant_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Number of grants"
    )

    @_typed_check("grant_count", name="grant_count_non_negative")
    def _check_grant_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate grant count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    chemical_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Number of chemicals"
    )

    @_typed_check("chemical_count", name="chemical_count_non_negative")
    def _check_chemical_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate chemical count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    # === Classification Data (JSON arrays extracted by transformer) ===
    subject_mesh: Series[str] = pa.Field(
        nullable=True,
        description="MeSH terms (JSON array of descriptor/qualifier strings)",
    )

    chemicals: Series[str] = pa.Field(
        nullable=True,
        description="Chemical substances (JSON array of name/registry pairs)",
    )

    subject_keywords: Series[str] = pa.Field(
        nullable=True,
        description="Author keywords (JSON array)",
    )

    databanks: Series[str] = pa.Field(
        nullable=True,
        description="Databank accession numbers (JSON array)",
    )

    gene_symbols: Series[str] = pa.Field(
        nullable=True,
        description="Gene symbols (JSON array)",
    )

    publication_types: Series[str] = pa.Field(
        nullable=True,
        description="Publication types (JSON array, e.g., Journal Article, Review)",
    )

    # === System Fields ===
    _source: Series[str] = pa.Field(
        nullable=False,
        eq="pubmed",
        description="Data source identifier",
    )

    # Note: accepted_date, received_date, revised_date, epub_date excluded from
    # transformer output per design (PubMed pipeline field exclusions)

    # Note: affiliation_list inherited from base (unified field name)

    # === Structured Author-Affiliation Mapping ===
    authors_with_affiliations: Series[str] = pa.Field(
        nullable=True,
        description="JSON array of authors with their affiliations and identifiers",
    )
    authors_with_affiliations_raw_json: Series[str] | None = pa.Field(
        nullable=True,
        description="Raw provider JSON for authors-with-affiliations payload.",
    )
    authors_with_affiliations_canonical_json: Series[str] | None = pa.Field(
        nullable=True,
        description="Canonical JSON companion for authors-with-affiliations payload.",
    )

    class Config:
        """Pandera configuration."""

        strict = False  # Allow missing columns and extra columns
        ordered = False  # Changed to False for inheritance compatibility
        coerce = True
        name = "PubMedPublicationSchema"
        description = "PubMed Publication Silver layer validation"
