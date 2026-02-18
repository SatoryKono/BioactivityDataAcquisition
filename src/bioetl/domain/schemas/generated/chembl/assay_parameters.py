# mypy: ignore-errors
"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""

# mypy: ignore-errors
from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

class ChemblAssayParametersSilverSchema(pa.DataFrameModel):
    """Generated Pandera schema from canonical schema registry."""

    entity_id: Series[str] | None = pa.Field(nullable=True)
    content_hash: Series[str] | None = pa.Field(nullable=True)
    _run_id: Series[str] | None = pa.Field(nullable=True)
    _run_type: Series[str] | None = pa.Field(nullable=True)
    _source_batch_id: Series[str] | None = pa.Field(nullable=True)
    _ingestion_ts: Series[str] | None = pa.Field(nullable=True)
    _index: Series[int] | None = pa.Field(nullable=True)
    assay_id: Series[str] | None = pa.Field(nullable=True)
    assay_param_id: Series[int] | None = pa.Field(nullable=True)
    comments: Series[str] | None = pa.Field(nullable=True)
    relation: Series[str] | None = pa.Field(nullable=True)
    standard_relation: Series[str] | None = pa.Field(nullable=True)
    standard_text_value: Series[str] | None = pa.Field(nullable=True)
    standard_type: Series[str] | None = pa.Field(nullable=True)
    standard_units: Series[str] | None = pa.Field(nullable=True)
    standard_value: Series[float] | None = pa.Field(nullable=True)
    text_value: Series[str] | None = pa.Field(nullable=True)
    type: Series[str] | None = pa.Field(nullable=True)
    units: Series[str] | None = pa.Field(nullable=True)
    value: Series[float] | None = pa.Field(nullable=True)
    _dq_error: Series[bool] | None = pa.Field(nullable=True)
    _dq_warn: Series[bool] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = True
        coerce = True
