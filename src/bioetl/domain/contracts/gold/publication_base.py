"""Base Gold schema for all publication entities.

This module provides a unified base schema that all provider-specific Gold
publication schemas inherit from. This ensures:
- Cross-provider query compatibility
- Consistent field naming and types
- Unified constraints (year range, nullable policy)
- DRY principle for shared fields

Int->Float coercion note:
    Fields marked with `coerce=True` and `Series[float]` that are `int64` in Silver
    use float to handle nullable integers. This is a deliberate design decision
    documented in RULES.md Section 2.6.

Unified constraints:
    - year: 1450-2150 (covers incunabula + future publications)
    - citation_count, reference_count: >= 0
    - doc_type: nullable=True (not all providers supply doc_type)
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class PublicationGoldBaseSchema(pa.DataFrameModel):
    """Unified base schema for Gold publication records.

    All provider-specific Gold schemas (PubMed, CrossRef, OpenAlex, SemanticScholar)
    inherit from this base. This ensures cross-provider query compatibility and
    consistent field definitions.

    Field Categories:
        - System Fields: entity_id, content_hash (non-nullable)
        - Cross-Reference IDs: doi, pmid, pmc_id (unified across providers)
        - Core Content: title, abstract, authors
        - Journal/Venue: journal, volume, issue, first_page, last_page
        - Dates: year (unified range), publication_date
        - Metadata: doc_type, language
        - Metrics: citation_count, reference_count
        - Lookup Tracking: source, lookup_method, original_id
        - DQ Fields: dq_warn, dq_error
        - Lineage: run_id, run_type, source_batch_id, ingestion_ts, index

    Note:
        Provider-specific primary keys (pmid, paper_id, openalex_id) are NOT in the
        base schema. Each provider schema defines its own primary key.
    """

    # === System Fields (non-nullable) ===
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # === Cross-Reference IDs (unified across providers) ===
    # doi: Digital Object Identifier (lowercase, without "https://doi.org/")
    doi: Series[str] = pa.Field(nullable=True)
    # pmid: PubMed ID (numeric string: "12345678")
    pmid: Series[str] = pa.Field(nullable=True)
    # pmc_id: PubMed Central ID (format: "PMC1234567")
    pmc_id: Series[str] = pa.Field(nullable=True)

    # === Core Content ===
    title: Series[str] = pa.Field(nullable=True)
    # authors: JSON-serialized list of author names/objects
    authors: Series[str] = pa.Field(nullable=True)

    # === Journal/Venue ===
    journal: Series[str] = pa.Field(nullable=True)
    volume: Series[str] = pa.Field(nullable=True)
    first_page: Series[str] = pa.Field(nullable=True)
    last_page: Series[str] = pa.Field(nullable=True)

    # === Dates (unified format: YYYY-MM-DD or YYYY) ===
    # year: Unified range 1450-2150 (covers incunabula through future)
    year: Series[float] = pa.Field(nullable=True, ge=1450, le=2150, coerce=True)
    publication_date: Series[str] = pa.Field(nullable=True)

    # === Metadata ===
    # doc_type: Unified nullable policy (not all providers supply doc_type)
    doc_type: Series[str] = pa.Field(nullable=True)
    language: Series[str] = pa.Field(nullable=True)

    # === Metrics ===
    citation_count: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    reference_count: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)

    # === Lookup Tracking ===
    # _source: Provider name (e.g., "pubmed", "crossref", "openalex", "s2")
    source: Series[str] = pa.Field(nullable=True, alias="_source")
    # _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
    lookup_method: Series[str] = pa.Field(nullable=True, alias="_lookup_method")
    # _original_id: Original identifier used for lookup
    original_id: Series[str] = pa.Field(nullable=True, alias="_original_id")

    # === DQ Fields ===
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # === Lineage Metadata ===
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = "filter"  # Allow subclasses to add fields


__all__ = ["PublicationGoldBaseSchema"]
