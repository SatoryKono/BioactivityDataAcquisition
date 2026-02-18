# mypy: ignore-errors
"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""

# mypy: ignore-errors
from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

class PubmedPublicationSilverSchema(pa.DataFrameModel):
    """Generated Pandera schema from canonical schema registry."""

    entity_id: Series[str] | None = pa.Field(nullable=True)
    content_hash: Series[str] | None = pa.Field(nullable=True)
    _run_id: Series[str] | None = pa.Field(nullable=True)
    _run_type: Series[str] | None = pa.Field(nullable=True)
    _source_batch_id: Series[str] | None = pa.Field(nullable=True)
    _source: Series[str] | None = pa.Field(nullable=True)
    _ingestion_ts: Series[str] | None = pa.Field(nullable=True)
    _index: Series[int] | None = pa.Field(nullable=True)
    _lookup_method: Series[str] | None = pa.Field(nullable=True)
    _original_id: Series[str] | None = pa.Field(nullable=True)
    abstract: Series[str] | None = pa.Field(nullable=True)
    affiliation_list: Series[str] | None = pa.Field(nullable=True)
    affiliation_structured: Series[str] | None = pa.Field(nullable=True)
    author_count: Series[int] | None = pa.Field(nullable=True)
    author_keys: Series[str] | None = pa.Field(nullable=True)
    authors: Series[str] | None = pa.Field(nullable=True)
    authors_with_affiliations: Series[str] | None = pa.Field(nullable=True)
    chemical_count: Series[int] | None = pa.Field(nullable=True)
    chemicals: Series[str] | None = pa.Field(nullable=True)
    citation_subset: Series[str] | None = pa.Field(nullable=True)
    citations_made: Series[int] | None = pa.Field(nullable=True)
    country: Series[str] | None = pa.Field(nullable=True)
    databanks: Series[str] | None = pa.Field(nullable=True)
    date_completed: Series[str] | None = pa.Field(nullable=True)
    date_revised: Series[str] | None = pa.Field(nullable=True)
    doi: Series[str] | None = pa.Field(nullable=True)
    gene_symbols: Series[str] | None = pa.Field(nullable=True)
    grant_count: Series[int] | None = pa.Field(nullable=True)
    issn: Series[str] | None = pa.Field(nullable=True)
    issue: Series[str] | None = pa.Field(nullable=True)
    journal: Series[str] | None = pa.Field(nullable=True)
    journal_iso_abbrev: Series[str] | None = pa.Field(nullable=True)
    journal_issn_type: Series[str] | None = pa.Field(nullable=True)
    journal_name_short: Series[str] | None = pa.Field(nullable=True)
    keyword_count: Series[int] | None = pa.Field(nullable=True)
    language: Series[str] | None = pa.Field(nullable=True)
    medline_pgn: Series[str] | None = pa.Field(nullable=True)
    mesh_heading_count: Series[int] | None = pa.Field(nullable=True)
    nlm_unique_id: Series[str] | None = pa.Field(nullable=True)
    page_first: Series[str] | None = pa.Field(nullable=True)
    page_last: Series[str] | None = pa.Field(nullable=True)
    page_range: Series[str] | None = pa.Field(nullable=True)
    pmc_id: Series[str] | None = pa.Field(nullable=True)
    pmid: Series[str] | None = pa.Field(nullable=True)
    pub_date: Series[str] | None = pa.Field(nullable=True)
    pub_day: Series[int] | None = pa.Field(nullable=True)
    pub_month: Series[int] | None = pa.Field(nullable=True)
    publication_class: Series[str] | None = pa.Field(nullable=True)
    publication_date: Series[str] | None = pa.Field(nullable=True)
    publication_status: Series[str] | None = pa.Field(nullable=True)
    publication_type: Series[str] | None = pa.Field(nullable=True)
    publication_type_list: Series[str] | None = pa.Field(nullable=True)
    publication_year: Series[int] | None = pa.Field(nullable=True)
    title: Series[str] | None = pa.Field(nullable=True)
    volume: Series[str] | None = pa.Field(nullable=True)
    _dq_error: Series[bool] | None = pa.Field(nullable=True)
    _dq_warn: Series[bool] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = True
        coerce = True
