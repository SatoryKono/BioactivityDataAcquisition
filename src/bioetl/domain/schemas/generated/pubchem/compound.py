# mypy: ignore-errors
"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""

# mypy: ignore-errors
from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

class PubchemCompoundSilverSchema(pa.DataFrameModel):
    """Generated Pandera schema from canonical schema registry."""

    entity_id: Series[str] | None = pa.Field(nullable=True)
    content_hash: Series[str] | None = pa.Field(nullable=True)
    _run_id: Series[str] | None = pa.Field(nullable=True)
    _run_type: Series[str] | None = pa.Field(nullable=True)
    _source_batch_id: Series[str] | None = pa.Field(nullable=True)
    _ingestion_ts: Series[str] | None = pa.Field(nullable=True)
    _index: Series[int] | None = pa.Field(nullable=True)
    canonical_smiles: Series[str] | None = pa.Field(nullable=True)
    molecule_id: Series[str] | None = pa.Field(nullable=True)
    complexity: Series[float] | None = pa.Field(nullable=True)
    conformer_count_3d: Series[float] | None = pa.Field(nullable=True)
    conformer_rmsd_3d: Series[float] | None = pa.Field(nullable=True)
    effective_rotor_count_3d: Series[float] | None = pa.Field(nullable=True)
    exact_mass: Series[float] | None = pa.Field(nullable=True)
    feature_acceptor_count_3d: Series[float] | None = pa.Field(nullable=True)
    feature_anion_count_3d: Series[float] | None = pa.Field(nullable=True)
    feature_cation_count_3d: Series[float] | None = pa.Field(nullable=True)
    feature_count_3d: Series[float] | None = pa.Field(nullable=True)
    feature_donor_count_3d: Series[float] | None = pa.Field(nullable=True)
    feature_hydrophobe_count_3d: Series[float] | None = pa.Field(nullable=True)
    feature_ring_count_3d: Series[float] | None = pa.Field(nullable=True)
    inchi: Series[str] | None = pa.Field(nullable=True)
    inchi_key: Series[str] | None = pa.Field(nullable=True)
    isomeric_smiles: Series[str] | None = pa.Field(nullable=True)
    iupac_name: Series[str] | None = pa.Field(nullable=True)
    molecular_formula: Series[str] | None = pa.Field(nullable=True)
    molecular_weight: Series[float] | None = pa.Field(nullable=True)
    monoisotopic_mass: Series[float] | None = pa.Field(nullable=True)
    tpsa: Series[float] | None = pa.Field(nullable=True)
    x_steric_quadrupole_3d: Series[float] | None = pa.Field(nullable=True)
    xlogp: Series[float] | None = pa.Field(nullable=True)
    y_steric_quadrupole_3d: Series[float] | None = pa.Field(nullable=True)
    z_steric_quadrupole_3d: Series[float] | None = pa.Field(nullable=True)
    _dq_error: Series[bool] | None = pa.Field(nullable=True)
    _dq_warn: Series[bool] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = True
        coerce = True
