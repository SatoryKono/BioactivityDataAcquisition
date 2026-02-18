# mypy: ignore-errors
"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""

# mypy: ignore-errors
from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

class ChemblAssaySilverSchema(pa.DataFrameModel):
    """Generated Pandera schema from canonical schema registry."""

    entity_id: Series[str] | None = pa.Field(nullable=True)
    content_hash: Series[str] | None = pa.Field(nullable=True)
    _run_id: Series[str] | None = pa.Field(nullable=True)
    _run_type: Series[str] | None = pa.Field(nullable=True)
    _source_batch_id: Series[str] | None = pa.Field(nullable=True)
    _ingestion_ts: Series[str] | None = pa.Field(nullable=True)
    _index: Series[int] | None = pa.Field(nullable=True)
    aidx: Series[str] | None = pa.Field(nullable=True)
    assay_category: Series[str] | None = pa.Field(nullable=True)
    assay_cell_type: Series[str] | None = pa.Field(nullable=True)
    assay_id: Series[str] | None = pa.Field(nullable=True)
    assay_classifications: Series[str] | None = pa.Field(nullable=True)
    assay_group: Series[str] | None = pa.Field(nullable=True)
    assay_organism: Series[str] | None = pa.Field(nullable=True)
    assay_parameters: Series[str] | None = pa.Field(nullable=True)
    assay_pref_name: Series[str] | None = pa.Field(nullable=True)
    assay_strain: Series[str] | None = pa.Field(nullable=True)
    assay_subcellular_fraction: Series[str] | None = pa.Field(nullable=True)
    assay_taxonomy_id: Series[float] | None = pa.Field(nullable=True)
    assay_test_type: Series[str] | None = pa.Field(nullable=True)
    assay_tissue: Series[str] | None = pa.Field(nullable=True)
    assay_type: Series[str] | None = pa.Field(nullable=True)
    assay_type_description: Series[str] | None = pa.Field(nullable=True)
    bao_format: Series[str] | None = pa.Field(nullable=True)
    bao_label: Series[str] | None = pa.Field(nullable=True)
    cell_id: Series[str] | None = pa.Field(nullable=True)
    confidence_description: Series[str] | None = pa.Field(nullable=True)
    confidence_score: Series[int] | None = pa.Field(nullable=True)
    description: Series[str] | None = pa.Field(nullable=True)
    publication_id: Series[str] | None = pa.Field(nullable=True)
    relationship_description: Series[str] | None = pa.Field(nullable=True)
    relationship_type: Series[str] | None = pa.Field(nullable=True)
    score: Series[float] | None = pa.Field(nullable=True)
    src_assay_id: Series[str] | None = pa.Field(nullable=True)
    src_id: Series[int] | None = pa.Field(nullable=True)
    target_id: Series[str] | None = pa.Field(nullable=True)
    tissue_id: Series[str] | None = pa.Field(nullable=True)
    variant_accession: Series[str] | None = pa.Field(nullable=True)
    variant_isoform: Series[str] | None = pa.Field(nullable=True)
    variant_mutation: Series[str] | None = pa.Field(nullable=True)
    variant_organism: Series[str] | None = pa.Field(nullable=True)
    variant_sequence: Series[str] | None = pa.Field(nullable=True)
    variant_sequence_json: Series[str] | None = pa.Field(nullable=True)
    variant_taxonomy_id: Series[float] | None = pa.Field(nullable=True)
    _dq_error: Series[bool] | None = pa.Field(nullable=True)
    _dq_warn: Series[bool] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = True
        coerce = True
