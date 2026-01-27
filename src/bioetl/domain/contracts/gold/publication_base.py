"""Base Gold schema for all publication entities."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class PublicationGoldBaseSchema(pa.DataFrameModel):
    """Unified base schema for Gold publication records.

    All provider-specific Gold schemas inherit from this.
    Ensures cross-provider query compatibility.
    """

    # === System Fields (non-nullable) ===
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # === Cross-Reference IDs (unified across providers) ===
    doi: Series[str] = pa.Field(nullable=True)
    pmid: Series[str] = pa.Field(nullable=True)
    pmc_id: Series[str] = pa.Field(nullable=True)

    # === Core Content ===
    title: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)  # Unified: include everywhere
    authors: Series[object] = pa.Field(nullable=True)   # JSON array (deserialized)

    # === Journal/Venue ===
    journal: Series[str] = pa.Field(nullable=True)
    volume: Series[str] = pa.Field(nullable=True)
    issue: Series[str] = pa.Field(nullable=True)
    first_page: Series[str] = pa.Field(nullable=True)
    last_page: Series[str] = pa.Field(nullable=True)

    # === Dates (unified format: YYYY-MM-DD or YYYY) ===
    year: Series[float] = pa.Field(nullable=True, ge=1450, le=2150, coerce=True)
    publication_date: Series[str] = pa.Field(nullable=True)

    # === Metadata ===
    doc_type: Series[str] = pa.Field(nullable=True)  # Unified: nullable
    language: Series[str] = pa.Field(nullable=True)

    # === Metrics ===
    citation_count: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    reference_count: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)

    # === Open Access ===
    is_oa: Series[bool] = pa.Field(nullable=True, coerce=True)
    oa_status: Series[str] = pa.Field(nullable=True)

    # === Classification (always list[str] in Gold) ===
    keywords: Series[object] = pa.Field(nullable=True)

    # === Lookup Tracking ===
    source: Series[str] = pa.Field(nullable=True, alias="_source")
    lookup_method: Series[str] = pa.Field(nullable=True, alias="_lookup_method")
    original_id: Series[str] = pa.Field(nullable=True, alias="_original_id")

    # === DQ Fields ===
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # === Lineage ===
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True
