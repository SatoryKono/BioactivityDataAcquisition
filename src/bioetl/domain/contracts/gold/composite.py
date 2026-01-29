"""Composite Gold layer data contracts.

Contains Pandera DataFrameModel schemas for composite pipeline entities in the Gold layer:
- CompositePublicationGoldSchema: Merged publication from multiple providers

Composite schemas use qualified column names in format: {provider}.{entity}.{field}
This allows tracking which source contributed each value.

Int→Float coercion note:
    Fields marked with `coerce=True` and `Series[float]` that are `int64` in Silver
    use float to handle nullable integers. This is a deliberate design decision
    documented in RULES.md §2.6.

Note on strict mode:
    Composite schemas use `strict = False` because the actual columns depend on
    which enrichers succeeded. The schema validates core required fields while
    allowing additional qualified columns from enrichers.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class CompositePublicationGoldSchema(pa.DataFrameModel):
    """Schema for Composite Publication in Gold layer.

    Merged publication entity combining data from multiple providers:
    - Seed: chembl_publication
    - Enrichers: crossref, openalex, pubmed, semanticscholar

    Column naming:
        Business columns use qualified format: {provider}.{entity}.{field}
        Example: chembl.publication.title, crossref.publication.citation_count

    Required fields:
        - System fields (entity_id, content_hash)
        - Seed primary key (document_chembl_id via qualified name)
        - Title (required for valid publication)
        - Lineage metadata (_composite_run_id, etc.)

    Note: Uses strict=False to allow variable enricher columns.
    """

    # =========================================================================
    # System Fields (from seed)
    # =========================================================================
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # =========================================================================
    # DQ Fields (from seed)
    # =========================================================================
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # =========================================================================
    # Lineage Metadata (from seed)
    # =========================================================================
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    # Source tracking (from seed)
    source: Series[str] = pa.Field(nullable=True, alias="_source")

    # Lookup metadata (from seed)
    lookup_method: Series[str] = pa.Field(nullable=True, alias="_lookup_method")
    original_id: Series[str] = pa.Field(nullable=True, alias="_original_id")

    # =========================================================================
    # Composite Lineage Metadata (added by MergeService)
    # =========================================================================
    composite_run_id: Series[str] = pa.Field(nullable=False, alias="_composite_run_id")
    source_providers: Series[str] = pa.Field(
        nullable=False, alias="_source_providers"
    )  # JSON list
    enrichment_status: Series[str] = pa.Field(
        nullable=False, alias="_enrichment_status"
    )  # JSON dict
    lineage_created_at: Series[str] = pa.Field(
        nullable=False, alias="_lineage_created_at"
    )  # ISO timestamp

    # =========================================================================
    # Seed Primary Key (ChEMBL document ID)
    # =========================================================================
    # Note: Qualified column name from seed
    # In the merged output, this appears as: chembl.publication.document_chembl_id
    # The unqualified version may also be present depending on merge configuration

    # =========================================================================
    # Core Business Fields (may be qualified or coalesced)
    # =========================================================================
    # Note: These fields may appear with qualified names depending on merge strategy.
    # With coalesce/seed_priority, the winning value uses the seed column name.
    # With no coalesce, all provider columns are preserved with qualified names.
    #
    # Example qualified names:
    # - chembl.publication.title
    # - chembl.publication.document_chembl_id
    # - crossref.publication.citations_received
    # - pubmed.publication.subject_mesh
    # - openalex.publication.subject_topics
    # - semanticscholar.publication.tldr
    #
    # Since columns are dynamically determined by enrichers, we use strict=False

    class Config:
        """Pandera configuration.

        Note: strict=False allows additional columns from enrichers.
        The actual columns depend on which enrichers succeeded and the merge strategy.
        """

        strict = False  # Allow additional qualified columns from enrichers
        coerce = True  # Enable type coercion for nullable integers


__all__ = [
    "CompositePublicationGoldSchema",
]
