# mypy: ignore-errors
"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""

# mypy: ignore-errors
from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

class ChemblProteinClassSilverSchema(pa.DataFrameModel):
    """Generated Pandera schema from canonical schema registry."""

    entity_id: Series[str] | None = pa.Field(nullable=True)
    content_hash: Series[str] | None = pa.Field(nullable=True)
    _run_id: Series[str] | None = pa.Field(nullable=True)
    _run_type: Series[str] | None = pa.Field(nullable=True)
    _source_batch_id: Series[str] | None = pa.Field(nullable=True)
    _ingestion_ts: Series[str] | None = pa.Field(nullable=True)
    _index: Series[int] | None = pa.Field(nullable=True)
    class_level: Series[int] | None = pa.Field(nullable=True)
    definition: Series[str] | None = pa.Field(nullable=True)
    downgraded: Series[int] | None = pa.Field(nullable=True)
    parent_id: Series[int] | None = pa.Field(nullable=True)
    pref_name: Series[str] | None = pa.Field(nullable=True)
    protein_class_desc: Series[str] | None = pa.Field(nullable=True)
    protein_class_id: Series[int] | None = pa.Field(nullable=True)
    replaced_by: Series[int] | None = pa.Field(nullable=True)
    short_name: Series[str] | None = pa.Field(nullable=True)
    sort_order: Series[int] | None = pa.Field(nullable=True)
    _dq_error: Series[bool] | None = pa.Field(nullable=True)
    _dq_warn: Series[bool] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = True
        coerce = True
