# mypy: ignore-errors
"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""

# mypy: ignore-errors
from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

class ChemblTargetComponentSilverSchema(pa.DataFrameModel):
    """Generated Pandera schema from canonical schema registry."""

    entity_id: Series[str] | None = pa.Field(nullable=True)
    content_hash: Series[str] | None = pa.Field(nullable=True)
    _run_id: Series[str] | None = pa.Field(nullable=True)
    _run_type: Series[str] | None = pa.Field(nullable=True)
    _source_batch_id: Series[str] | None = pa.Field(nullable=True)
    _ingestion_ts: Series[str] | None = pa.Field(nullable=True)
    _index: Series[int] | None = pa.Field(nullable=True)
    accession: Series[str] | None = pa.Field(nullable=True)
    component_id: Series[int] | None = pa.Field(nullable=True)
    component_type: Series[str] | None = pa.Field(nullable=True)
    description: Series[str] | None = pa.Field(nullable=True)
    organism: Series[str] | None = pa.Field(nullable=True)
    protein_classification_id: Series[int] | None = pa.Field(nullable=True)
    protein_classifications: Series[str] | None = pa.Field(nullable=True)
    target_component_synonyms: Series[str] | None = pa.Field(nullable=True)
    target_component_xrefs: Series[str] | None = pa.Field(nullable=True)
    taxonomy_id: Series[int] | None = pa.Field(nullable=True)
    _dq_error: Series[bool] | None = pa.Field(nullable=True)
    _dq_warn: Series[bool] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = True
        coerce = True
