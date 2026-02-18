# mypy: ignore-errors
"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""

# mypy: ignore-errors
from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

class SemanticscholarPublicationSilverSchema(pa.DataFrameModel):
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
    author_h_indices: Series[str] | None = pa.Field(nullable=True)
    author_keys: Series[str] | None = pa.Field(nullable=True)
    author_orcids: Series[str] | None = pa.Field(nullable=True)
    author_s2_ids: Series[str] | None = pa.Field(nullable=True)
    citation_contexts: Series[str] | None = pa.Field(nullable=True)
    citations_made: Series[int] | None = pa.Field(nullable=True)
    citations_received: Series[int] | None = pa.Field(nullable=True)
    corpus_id: Series[int] | None = pa.Field(nullable=True)
    dblp_id: Series[str] | None = pa.Field(nullable=True)
    doi: Series[str] | None = pa.Field(nullable=True)
    influential_citation_count: Series[int] | None = pa.Field(nullable=True)
    is_oa: Series[bool] | None = pa.Field(nullable=True)
    issue: Series[str] | None = pa.Field(nullable=True)
    journal: Series[str] | None = pa.Field(nullable=True)
    oa_status: Series[str] | None = pa.Field(nullable=True)
    open_access_url: Series[str] | None = pa.Field(nullable=True)
    page_first: Series[str] | None = pa.Field(nullable=True)
    page_last: Series[str] | None = pa.Field(nullable=True)
    page_range: Series[str] | None = pa.Field(nullable=True)
    paper_id: Series[str] | None = pa.Field(nullable=True)
    pmid: Series[str] | None = pa.Field(nullable=True)
    publication_class: Series[str] | None = pa.Field(nullable=True)
    publication_date: Series[str] | None = pa.Field(nullable=True)
    publication_types: Series[str] | None = pa.Field(nullable=True)
    publication_year: Series[int] | None = pa.Field(nullable=True)
    subject_fields: Series[str] | None = pa.Field(nullable=True)
    title: Series[str] | None = pa.Field(nullable=True)
    tldr: Series[str] | None = pa.Field(nullable=True)
    volume: Series[str] | None = pa.Field(nullable=True)
    _dq_error: Series[bool] | None = pa.Field(nullable=True)
    _dq_warn: Series[bool] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = True
        coerce = True
