"""Base Pandera schema for all ETL records.

Contains common metadata fields required by RULES.md §2.4.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

import pandera as pa
from pandera.typing import Series


class ETLRecordSchema(pa.DataFrameModel):
    """Base schema with common system and lineage fields."""

    # === System Fields ===
    entity_id: Series[str] = pa.Field(
        nullable=False, description="Unique business identifier for the entity."
    )
    content_hash: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^[a-f0-9]{64}$",
        description="SHA256 hash of canonical record representation for versioning.",
    )

    # === Lineage & DQ Fields (from RULES.md §2.4) ===
    _run_id: Series[UUID] = pa.Field(nullable=False, description="Correlation ID for the pipeline run.")
    _run_type: Series[str] = pa.Field(
        nullable=False,
        isin=["incremental", "backfill", "rebuild"],
        description="Type of pipeline run.",
    )
    _source_batch_id: Optional[Series[UUID]] = pa.Field(
        nullable=True, description="Batch context ID from the source."
    )
    _ingestion_ts: Series[datetime] = pa.Field(
        nullable=False, description="Timestamp when the record was ingested (UTC)."
    )
    _dq_warn: Series[bool] = pa.Field(
        nullable=False, default=False, description="Flag for data quality warnings."
    )
    _index: Series[int] = pa.Field(
        nullable=False, ge=0, description="Sequential index of the record in the pipeline run."
    )

    class Config:
        """Pandera configuration."""

        strict = True  # Disallow columns not specified in the schema
        ordered = True  # Enforce column order
        coerce = True  # Coerce data types to match schema
