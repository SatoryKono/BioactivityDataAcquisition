"""Base Pandera schema for all ETL records.

Contains common metadata fields required by RULES.md §2.4.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast

import pandera.pandas as pa
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
        description="SHA256 hash of canonical record representation (64 hex chars).",
    )

    # === Lineage & DQ Fields (from RULES.md §2.4) ===
    run_id: Series[object] = pa.Field(
        alias="_run_id",
        nullable=False,
        description="Correlation ID for the pipeline run.",
    )
    run_type: Series[str] = pa.Field(
        alias="_run_type",
        nullable=False,
        description="Type of pipeline run.",
    )

    @pa.check("_run_type", name="run_type_values")
    def _check_run_type(cls, series: Series[str]) -> Series[bool]:  # noqa: N805
        """Validate _run_type values."""
        return cast("Series[bool]", series.isin(["incremental", "backfill", "rebuild"]))

    source_batch_id: Series[object] | None = pa.Field(
        alias="_source_batch_id",
        nullable=True,
        description="Batch context ID from the source.",
    )
    ingestion_ts: Series[datetime] = pa.Field(
        alias="_ingestion_ts",
        nullable=False,
        description="Timestamp when the record was ingested (UTC).",
    )

    @pa.check("_ingestion_ts", name="ingestion_ts_not_future")
    def _check_ingestion_ts(cls, series: Series[datetime]) -> Series[bool]:  # noqa: N805
        """Ensure ingestion timestamp is not in the future."""
        # Note: In practice, we just check it's a valid datetime
        return cast("Series[bool]", series <= datetime.now(series.dt.tz))

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
    index: Series[int] = pa.Field(
        alias="_index",
        nullable=False,
        description="Sequential index of the record in the pipeline run.",
    )

    @pa.check("_index", name="index_non_negative")
    def _check_index(cls, series: Series[int]) -> Series[bool]:  # noqa: N805
        """Validate index is non-negative."""
        return cast("Series[bool]", series >= 0)

    class Config:
        """Pandera configuration."""

        strict = True  # Disallow columns not specified in the schema
        ordered = True  # Enforce column order
        coerce = True  # Coerce data types to match schema
