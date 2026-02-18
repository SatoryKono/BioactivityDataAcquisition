# mypy: ignore-errors
"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""

# mypy: ignore-errors
from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

class CrossrefPublicationSilverSchema(pa.DataFrameModel):
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
    author_details: Series[str] | None = pa.Field(nullable=True)
    author_keys: Series[str] | None = pa.Field(nullable=True)
    author_orcids: Series[str] | None = pa.Field(nullable=True)
    authors: Series[str] | None = pa.Field(nullable=True)
    citations_made: Series[int] | None = pa.Field(nullable=True)
    content_domain_crossmark_restriction: Series[bool] | None = pa.Field(nullable=True)
    doi: Series[str] | None = pa.Field(nullable=True)
    issn: Series[str] | None = pa.Field(nullable=True)
    issn_electronic: Series[str] | None = pa.Field(nullable=True)
    issn_list: Series[str] | None = pa.Field(nullable=True)
    issn_print: Series[str] | None = pa.Field(nullable=True)
    issue: Series[str] | None = pa.Field(nullable=True)
    journal: Series[str] | None = pa.Field(nullable=True)
    journal_name_short: Series[str] | None = pa.Field(nullable=True)
    language: Series[str] | None = pa.Field(nullable=True)
    license_url: Series[str] | None = pa.Field(nullable=True)
    page_first: Series[str] | None = pa.Field(nullable=True)
    page_last: Series[str] | None = pa.Field(nullable=True)
    pmc_id: Series[str] | None = pa.Field(nullable=True)
    pmid: Series[str] | None = pa.Field(nullable=True)
    publication_class: Series[str] | None = pa.Field(nullable=True)
    publication_date: Series[str] | None = pa.Field(nullable=True)
    publication_year: Series[int] | None = pa.Field(nullable=True)
    published: Series[str] | None = pa.Field(nullable=True)
    published_online: Series[str] | None = pa.Field(nullable=True)
    published_print: Series[str] | None = pa.Field(nullable=True)
    publisher: Series[str] | None = pa.Field(nullable=True)
    references: Series[str] | None = pa.Field(nullable=True)
    title: Series[str] | None = pa.Field(nullable=True)
    volume: Series[str] | None = pa.Field(nullable=True)
    _dq_error: Series[bool] | None = pa.Field(nullable=True)
    _dq_warn: Series[bool] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = True
        coerce = True
