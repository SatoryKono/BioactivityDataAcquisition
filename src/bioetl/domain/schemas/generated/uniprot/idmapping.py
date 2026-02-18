# mypy: ignore-errors
"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""

# mypy: ignore-errors
from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

class UniprotIdmappingSilverSchema(pa.DataFrameModel):
    """Generated Pandera schema from canonical schema registry."""

    entity_id: Series[str] | None = pa.Field(nullable=True)
    content_hash: Series[str] | None = pa.Field(nullable=True)
    _run_id: Series[str] | None = pa.Field(nullable=True)
    _run_type: Series[str] | None = pa.Field(nullable=True)
    _source_batch_id: Series[str] | None = pa.Field(nullable=True)
    _ingestion_ts: Series[str] | None = pa.Field(nullable=True)
    _index: Series[int] | None = pa.Field(nullable=True)
    all_mappings: Series[str] | None = pa.Field(nullable=True)
    annotation_score: Series[int] | None = pa.Field(nullable=True)
    gene_primary: Series[str] | None = pa.Field(nullable=True)
    mapping_status: Series[str] | None = pa.Field(nullable=True)
    organism_common: Series[str] | None = pa.Field(nullable=True)
    organism_scientific: Series[str] | None = pa.Field(nullable=True)
    protein_name: Series[str] | None = pa.Field(nullable=True)
    reviewed: Series[bool] | None = pa.Field(nullable=True)
    sequence_length: Series[int] | None = pa.Field(nullable=True)
    sequence_mass: Series[int] | None = pa.Field(nullable=True)
    target_id: Series[str] | None = pa.Field(nullable=True)
    taxonomy_id: Series[int] | None = pa.Field(nullable=True)
    uniprot_accession: Series[str] | None = pa.Field(nullable=True)
    uniprot_entry_name: Series[str] | None = pa.Field(nullable=True)
    _dq_error: Series[bool] | None = pa.Field(nullable=True)
    _dq_warn: Series[bool] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = True
        coerce = True
