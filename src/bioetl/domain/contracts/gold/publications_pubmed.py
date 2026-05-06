# mypy: disable-error-code="misc"
"""PubMed publication schema for Gold contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold._publication_common_schema import (
    PublicationGoldCommonSchema,
)


class PubMedPublicationGoldSchema(PublicationGoldCommonSchema):
    """Schema for PubMed publication in Gold layer."""

    pmid: Series[str] = pa.Field(nullable=False)
    title: Series[str] = pa.Field(nullable=False)
    abstract_structured: Series[bool] = pa.Field(nullable=True)
    journal_name_short: Series[str] = pa.Field(nullable=True)
    journal_iso_abbrev: Series[str] = pa.Field(nullable=True)
    journal_issn_type: Series[str] = pa.Field(nullable=True)
    issn: Series[str] = pa.Field(nullable=True)
    nlm_unique_id: Series[str] = pa.Field(nullable=True)
    page_range: Series[str] = pa.Field(nullable=True)
    medline_pgn: Series[str] = pa.Field(nullable=True)
    author_keys: Series[str] = pa.Field(nullable=True)
    authors_with_affiliations: Series[str] = pa.Field(nullable=True)
    authors_with_affiliations_raw_json: Series[str] = pa.Field(nullable=True)
    authors_with_affiliations_canonical_json: Series[str] = pa.Field(nullable=True)
    affiliation_structured: Series[str] = pa.Field(nullable=True)
    affiliation_structured_raw_json: Series[str] = pa.Field(nullable=True)
    affiliation_structured_canonical_json: Series[str] = pa.Field(nullable=True)
    pii: Series[str] = pa.Field(nullable=True)
    mid: Series[str] = pa.Field(nullable=True)
    publisher_id: Series[str] = pa.Field(nullable=True)
    pub_month: Series[float] = pa.Field(nullable=True, coerce=True)
    pub_day: Series[float] = pa.Field(nullable=True, coerce=True)
    date_completed: Series[str] = pa.Field(nullable=True)
    date_revised: Series[str] = pa.Field(nullable=True)
    publication_status: Series[str] = pa.Field(nullable=True)
    publication_types: Series[str] = pa.Field(nullable=True)
    subject_keywords: Series[str] = pa.Field(nullable=True)
    subject_mesh: Series[str] = pa.Field(nullable=True)
    chemicals: Series[str] = pa.Field(nullable=True)
    databanks: Series[str] = pa.Field(nullable=True)
    gene_symbols: Series[str] = pa.Field(nullable=True)
    citation_subset: Series[str] = pa.Field(nullable=True)
    language: Series[str] = pa.Field(nullable=True)
    country: Series[str] = pa.Field(nullable=True)
    author_count: Series[float] = pa.Field(nullable=True, coerce=True)
    mesh_heading_count: Series[float] = pa.Field(nullable=True, coerce=True)
    keyword_count: Series[float] = pa.Field(nullable=True, coerce=True)
    grant_count: Series[float] = pa.Field(nullable=True, coerce=True)
    chemical_count: Series[float] = pa.Field(nullable=True, coerce=True)
    pub_date: Series[str] = pa.Field(nullable=True)


__all__ = ["PubMedPublicationGoldSchema"]
