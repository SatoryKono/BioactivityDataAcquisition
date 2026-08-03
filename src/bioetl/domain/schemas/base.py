# mypy: disable-error-code="misc"
"""Base Pandera schema for all ETL records.

Contains common metadata fields required by RULES.md §2.4.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

__all__ = [
    "ISO8601_TIMESTAMP_REGEX",
    "ETLRecordSchema",
]


# Regex pattern for ISO 8601 timestamp validation (YYYY-MM-DDTHH:MM:SS with optional subseconds and timezone)
# Matches: 2024-01-15T10:30:00, 2024-01-15T10:30:00.123456, 2024-01-15T10:30:00+00:00
ISO8601_TIMESTAMP_REGEX = (
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$"
)


class ETLRecordSchema(pa.DataFrameModel):
    """Base schema with common system and lineage fields."""

    # === System Fields ===
    entity_id: Series[str] = pa.Field(
        nullable=False, description="Unique business identifier for the entity."
    )
    content_hash: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^[a-f0-9]{64}$",
        description="SHA256 hash of canonical record representation (64 hex chars).",
    )

    # === Lineage & DQ Fields (from RULES.md §2.4) ===
    run_id: Series[str] = pa.Field(
        alias="_run_id",
        nullable=False,
        description="Correlation ID for the pipeline run.",
    )
    run_type: Series[str] = pa.Field(
        alias="_run_type",
        nullable=False,
        isin=["incremental", "backfill", "rebuild"],
        description="Type of pipeline run.",
    )

    source_batch_id: Series[str] | None = pa.Field(
        alias="_source_batch_id",
        nullable=True,
        description="Batch context ID from the source.",
    )
    ingestion_ts: Series[str] = pa.Field(
        alias="_ingestion_ts",
        nullable=False,
        str_matches=ISO8601_TIMESTAMP_REGEX,
        description="Timestamp when the record was ingested (UTC, ISO 8601 format).",
    )
    index: Series[int] = pa.Field(
        alias="_index",
        nullable=False,
        ge=0,
        description="Sequential index of the record in the pipeline run.",
    )

    dq_warn: Series[bool] = pa.Field(
        alias="_dq_warn",
        nullable=False,
        default=False,
        description="Flag for data quality warnings.",
    )
    dq_error: Series[bool] = pa.Field(
        alias="_dq_error",
        nullable=False,
        default=False,
        description="Flag for data quality errors.",
    )

    class Config:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Pandera configuration."""

        strict = True  # Disallow columns not specified in the schema
        ordered = True  # Enforce column order
        coerce = True  # Coerce data types to match schema
