# mypy: ignore-errors
"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""

# mypy: ignore-errors
from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

class ChemblMoleculeSilverSchema(pa.DataFrameModel):
    """Generated Pandera schema from canonical schema registry."""

    entity_id: Series[str] | None = pa.Field(nullable=True)
    content_hash: Series[str] | None = pa.Field(nullable=True)
    _run_id: Series[str] | None = pa.Field(nullable=True)
    _run_type: Series[str] | None = pa.Field(nullable=True)
    _source_batch_id: Series[str] | None = pa.Field(nullable=True)
    _ingestion_ts: Series[str] | None = pa.Field(nullable=True)
    _index: Series[int] | None = pa.Field(nullable=True)
    atc_classifications: Series[str] | None = pa.Field(nullable=True)
    availability_type: Series[float] | None = pa.Field(nullable=True)
    black_box_warning: Series[int] | None = pa.Field(nullable=True)
    canonical_smiles: Series[str] | None = pa.Field(nullable=True)
    chirality: Series[int] | None = pa.Field(nullable=True)
    cross_references: Series[str] | None = pa.Field(nullable=True)
    dosed_ingredient: Series[int] | None = pa.Field(nullable=True)
    first_approval: Series[float] | None = pa.Field(nullable=True)
    first_in_class: Series[int] | None = pa.Field(nullable=True)
    helm_notation: Series[str] | None = pa.Field(nullable=True)
    hierarchy_active_chembl_id: Series[str] | None = pa.Field(nullable=True)
    hierarchy_child_chembl_id: Series[str] | None = pa.Field(nullable=True)
    hierarchy_parent_chembl_id: Series[str] | None = pa.Field(nullable=True)
    inchi_key: Series[str] | None = pa.Field(nullable=True)
    inorganic_flag: Series[int] | None = pa.Field(nullable=True)
    max_phase: Series[int] | None = pa.Field(nullable=True)
    molecule_id: Series[str] | None = pa.Field(nullable=True)
    molecule_hierarchy: Series[str] | None = pa.Field(nullable=True)
    molecule_properties: Series[str] | None = pa.Field(nullable=True)
    molecule_species: Series[str] | None = pa.Field(nullable=True)
    molecule_structures: Series[str] | None = pa.Field(nullable=True)
    molecule_synonyms: Series[str] | None = pa.Field(nullable=True)
    molecule_type: Series[str] | None = pa.Field(nullable=True)
    natural_product: Series[int] | None = pa.Field(nullable=True)
    oral: Series[bool] | None = pa.Field(nullable=True)
    parenteral: Series[bool] | None = pa.Field(nullable=True)
    polymer_flag: Series[int] | None = pa.Field(nullable=True)
    pref_name: Series[str] | None = pa.Field(nullable=True)
    prodrug: Series[int] | None = pa.Field(nullable=True)
    aromatic_ring_count: Series[int] | None = pa.Field(nullable=True)
    hba_count: Series[int] | None = pa.Field(nullable=True)
    hbd_count: Series[int] | None = pa.Field(nullable=True)
    heavy_atom_count: Series[int] | None = pa.Field(nullable=True)
    logp: Series[float] | None = pa.Field(nullable=True)
    logp_method: Series[str] | None = pa.Field(nullable=True)
    molecular_formula: Series[str] | None = pa.Field(nullable=True)
    molecular_weight: Series[float] | None = pa.Field(nullable=True)
    mw_freebase: Series[float] | None = pa.Field(nullable=True)
    polar_surface_area: Series[float] | None = pa.Field(nullable=True)
    qed_score: Series[float] | None = pa.Field(nullable=True)
    ro3_pass: Series[str] | None = pa.Field(nullable=True)
    ro5_violation_count: Series[int] | None = pa.Field(nullable=True)
    rotatable_bond_count: Series[int] | None = pa.Field(nullable=True)
    standard_inchi: Series[str] | None = pa.Field(nullable=True)
    structure_type: Series[str] | None = pa.Field(nullable=True)
    therapeutic_flag: Series[bool] | None = pa.Field(nullable=True)
    topical: Series[bool] | None = pa.Field(nullable=True)
    usan_stem: Series[str] | None = pa.Field(nullable=True)
    usan_stem_definition: Series[str] | None = pa.Field(nullable=True)
    usan_substem: Series[str] | None = pa.Field(nullable=True)
    usan_year: Series[float] | None = pa.Field(nullable=True)
    withdrawn_flag: Series[bool] | None = pa.Field(nullable=True)
    _dq_error: Series[bool] | None = pa.Field(nullable=True)
    _dq_warn: Series[bool] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = True
        coerce = True
