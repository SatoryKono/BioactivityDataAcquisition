# mypy: ignore-errors
"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""

# mypy: ignore-errors
from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

class ChemblActivitySilverSchema(pa.DataFrameModel):
    """Generated Pandera schema from canonical schema registry."""

    entity_id: Series[str] | None = pa.Field(nullable=True)
    content_hash: Series[str] | None = pa.Field(nullable=True)
    _run_id: Series[str] | None = pa.Field(nullable=True)
    _run_type: Series[str] | None = pa.Field(nullable=True)
    _source_batch_id: Series[str] | None = pa.Field(nullable=True)
    _ingestion_ts: Series[str] | None = pa.Field(nullable=True)
    _index: Series[int] | None = pa.Field(nullable=True)
    action_type: Series[str] | None = pa.Field(nullable=True)
    action_type_description: Series[str] | None = pa.Field(nullable=True)
    action_type_parent_type: Series[str] | None = pa.Field(nullable=True)
    activity_comment: Series[str] | None = pa.Field(nullable=True)
    activity_id: Series[str] | None = pa.Field(nullable=True)
    activity_properties: Series[str] | None = pa.Field(nullable=True)
    assay_id: Series[str] | None = pa.Field(nullable=True)
    assay_description: Series[str] | None = pa.Field(nullable=True)
    assay_type: Series[str] | None = pa.Field(nullable=True)
    assay_variant_accession: Series[str] | None = pa.Field(nullable=True)
    assay_variant_mutation: Series[str] | None = pa.Field(nullable=True)
    bao_endpoint: Series[str] | None = pa.Field(nullable=True)
    bao_format: Series[str] | None = pa.Field(nullable=True)
    bao_label: Series[str] | None = pa.Field(nullable=True)
    canonical_smiles: Series[str] | None = pa.Field(nullable=True)
    data_validity_comment: Series[str] | None = pa.Field(nullable=True)
    data_validity_description: Series[str] | None = pa.Field(nullable=True)
    publication_id: Series[str] | None = pa.Field(nullable=True)
    journal: Series[str] | None = pa.Field(nullable=True)
    publication_year: Series[int] | None = pa.Field(nullable=True)
    ligand_efficiency_bei: Series[float] | None = pa.Field(nullable=True)
    ligand_efficiency_le: Series[float] | None = pa.Field(nullable=True)
    ligand_efficiency_lle: Series[float] | None = pa.Field(nullable=True)
    ligand_efficiency_sei: Series[float] | None = pa.Field(nullable=True)
    manual_curation_flag: Series[float] | None = pa.Field(nullable=True)
    molecule_id: Series[str] | None = pa.Field(nullable=True)
    molecule_pref_name: Series[str] | None = pa.Field(nullable=True)
    original_activity_id: Series[float] | None = pa.Field(nullable=True)
    parent_molecule_id: Series[str] | None = pa.Field(nullable=True)
    pchembl_value: Series[float] | None = pa.Field(nullable=True)
    potential_duplicate: Series[int] | None = pa.Field(nullable=True)
    qudt_units: Series[str] | None = pa.Field(nullable=True)
    record_id: Series[int] | None = pa.Field(nullable=True)
    relation: Series[str] | None = pa.Field(nullable=True)
    src_id: Series[int] | None = pa.Field(nullable=True)
    standard_flag: Series[int] | None = pa.Field(nullable=True)
    standard_relation: Series[str] | None = pa.Field(nullable=True)
    standard_text_value: Series[str] | None = pa.Field(nullable=True)
    standard_type: Series[str] | None = pa.Field(nullable=True)
    standard_units: Series[str] | None = pa.Field(nullable=True)
    standard_upper_value: Series[float] | None = pa.Field(nullable=True)
    standard_value: Series[float] | None = pa.Field(nullable=True)
    target_id: Series[str] | None = pa.Field(nullable=True)
    target_organism: Series[str] | None = pa.Field(nullable=True)
    target_pref_name: Series[str] | None = pa.Field(nullable=True)
    target_taxonomy_id: Series[float] | None = pa.Field(nullable=True)
    text_value: Series[str] | None = pa.Field(nullable=True)
    toid: Series[float] | None = pa.Field(nullable=True)
    type: Series[str] | None = pa.Field(nullable=True)
    units: Series[str] | None = pa.Field(nullable=True)
    uo_units: Series[str] | None = pa.Field(nullable=True)
    upper_value: Series[float] | None = pa.Field(nullable=True)
    value: Series[float] | None = pa.Field(nullable=True)
    _dq_error: Series[bool] | None = pa.Field(nullable=True)
    _dq_warn: Series[bool] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = True
        coerce = True
