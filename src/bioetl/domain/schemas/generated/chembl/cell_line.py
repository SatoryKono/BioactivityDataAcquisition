# mypy: ignore-errors
"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""

# mypy: ignore-errors
from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

class ChemblCellLineSilverSchema(pa.DataFrameModel):
    """Generated Pandera schema from canonical schema registry."""

    entity_id: Series[str] | None = pa.Field(nullable=True)
    content_hash: Series[str] | None = pa.Field(nullable=True)
    _run_id: Series[str] | None = pa.Field(nullable=True)
    _run_type: Series[str] | None = pa.Field(nullable=True)
    _source_batch_id: Series[str] | None = pa.Field(nullable=True)
    _ingestion_ts: Series[str] | None = pa.Field(nullable=True)
    _index: Series[int] | None = pa.Field(nullable=True)
    cell_id: Series[str] | None = pa.Field(nullable=True)
    cell_description: Series[str] | None = pa.Field(nullable=True)
    cell_name: Series[str] | None = pa.Field(nullable=True)
    cell_source_organism: Series[str] | None = pa.Field(nullable=True)
    cell_source_tissue: Series[str] | None = pa.Field(nullable=True)
    cellosaurus_id: Series[str] | None = pa.Field(nullable=True)
    cl_lincs_id: Series[str] | None = pa.Field(nullable=True)
    efo_id: Series[str] | None = pa.Field(nullable=True)
    _dq_error: Series[bool] | None = pa.Field(nullable=True)
    _dq_warn: Series[bool] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = True
        coerce = True
