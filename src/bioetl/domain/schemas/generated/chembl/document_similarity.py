# mypy: ignore-errors
"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""

# mypy: ignore-errors
from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

class ChemblDocumentSimilaritySilverSchema(pa.DataFrameModel):
    """Generated Pandera schema from canonical schema registry."""

    entity_id: Series[str] | None = pa.Field(nullable=True)
    content_hash: Series[str] | None = pa.Field(nullable=True)
    _run_id: Series[str] | None = pa.Field(nullable=True)
    _run_type: Series[str] | None = pa.Field(nullable=True)
    _source_batch_id: Series[str] | None = pa.Field(nullable=True)
    _ingestion_ts: Series[str] | None = pa.Field(nullable=True)
    _index: Series[int] | None = pa.Field(nullable=True)
    avg_tani: Series[float] | None = pa.Field(nullable=True)
    doc_1: Series[int] | None = pa.Field(nullable=True)
    doc_2: Series[int] | None = pa.Field(nullable=True)
    max_tani: Series[float] | None = pa.Field(nullable=True)
    mol_tani: Series[float] | None = pa.Field(nullable=True)
    pubmed_id1: Series[str] | None = pa.Field(nullable=True)
    pubmed_id2: Series[str] | None = pa.Field(nullable=True)
    sim_id: Series[int] | None = pa.Field(nullable=True)
    tid_tani: Series[float] | None = pa.Field(nullable=True)
    _dq_error: Series[bool] | None = pa.Field(nullable=True)
    _dq_warn: Series[bool] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = True
        coerce = True
