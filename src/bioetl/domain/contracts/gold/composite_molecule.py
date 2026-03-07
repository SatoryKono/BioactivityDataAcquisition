"""Composite molecule Gold schema."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class CompositeMoleculeGoldSchema(pa.DataFrameModel):
    """Schema for Composite Molecule in Gold layer."""

    entity_id: Series[str] = pa.Field(
        nullable=False,
        description="Stable business identifier for merged molecule entity.",
    )

    dq_warn: Series[bool] = pa.Field(
        nullable=False,
        default=False,
        alias="_dq_warn",
        description="Soft data-quality warning flag.",
    )
    dq_error: Series[bool] = pa.Field(
        nullable=False,
        default=False,
        alias="_dq_error",
        description="Hard data-quality error flag.",
    )

    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    composite_run_id: Series[str] = pa.Field(nullable=False, alias="_composite_run_id")
    source_providers: Series[str] = pa.Field(nullable=False, alias="_source_providers")
    enrichment_status: Series[str] = pa.Field(
        nullable=False, alias="_enrichment_status"
    )
    lineage_created_at: Series[str] = pa.Field(
        nullable=False,
        alias="_lineage_created_at",
    )

    class Config:
        """Pandera configuration."""

        strict = False
        coerce = True
