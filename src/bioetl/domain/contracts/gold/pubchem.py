# mypy: disable-error-code="misc"
"""PubChem Gold layer data contracts.

Contains Pandera DataFrameModel schemas for PubChem entities in the Gold layer:
- Compound: Chemical structures and identifiers from PubChem

Int→Float coercion note:
    Fields marked with `coerce=True` and `Series[float]` that are `int64` in Silver
    use float to handle nullable integers. This is a deliberate design decision
    documented in RULES.md §2.6.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold._strict_gold_contract_schema import (
    StrictGoldContractSchema,
)


class PubChemCompoundGoldSchema(StrictGoldContractSchema):
    """Schema for PubChem Compound in Gold layer.

    Aligned with domain/entities/pubchem.py (PubchemMolecule domain entity)
    and application/pipelines/pubchem/transformer.py (PubChemCompoundTransformer).
    The schema name follows the stable public pipeline surface (`compound`),
    while the canonical domain entity remains `PubchemMolecule`.
    """

    entity_id: Series[str] = pa.Field(nullable=False)
    molecule_id: Series[str] = pa.Field(
        nullable=False
    )  # Canonical molecule id (was cid)
    molecular_formula: Series[str] = pa.Field(nullable=True)
    molecular_weight: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # Transformed to float by transformer
    canonical_smiles: Series[str] = pa.Field(nullable=True)
    isomeric_smiles: Series[str] = pa.Field(nullable=True)
    inchi: Series[str] = pa.Field(nullable=True)
    inchi_key: Series[str] = pa.Field(nullable=True)
    standardized_canonical_smiles: Series[str] = pa.Field(nullable=True)
    standardized_isomeric_smiles: Series[str] = pa.Field(nullable=True)
    standardized_inchi: Series[str] = pa.Field(nullable=True)
    standardized_inchi_key: Series[str] = pa.Field(nullable=True)
    structure_parent_key: Series[str] = pa.Field(nullable=True)
    chemical_standardization_status: Series[str] = pa.Field(nullable=True)
    chemical_standardization_warnings: Series[str] = pa.Field(nullable=True)
    chemical_standardization_policy_version: Series[str] = pa.Field(nullable=True)
    logp: Series[float] = pa.Field(nullable=True, coerce=True, alias="xlogp")
    polar_surface_area: Series[float] = pa.Field(
        nullable=True, coerce=True, alias="tpsa"
    )
    iupac_name: Series[str] = pa.Field(nullable=True)
    content_hash: Series[str] = pa.Field(nullable=False)

    # 3D molecular descriptors
    complexity: Series[float] = pa.Field(nullable=True, coerce=True)
    conformer_count_3d: Series[float] = pa.Field(nullable=True, coerce=True)
    conformer_rmsd_3d: Series[float] = pa.Field(nullable=True, coerce=True)
    effective_rotor_count_3d: Series[float] = pa.Field(nullable=True, coerce=True)
    exact_mass: Series[float] = pa.Field(nullable=True, coerce=True)
    feature_acceptor_count_3d: Series[float] = pa.Field(nullable=True, coerce=True)
    feature_anion_count_3d: Series[float] = pa.Field(nullable=True, coerce=True)
    feature_cation_count_3d: Series[float] = pa.Field(nullable=True, coerce=True)
    feature_count_3d: Series[float] = pa.Field(nullable=True, coerce=True)
    feature_donor_count_3d: Series[float] = pa.Field(nullable=True, coerce=True)
    feature_hydrophobe_count_3d: Series[float] = pa.Field(nullable=True, coerce=True)
    feature_ring_count_3d: Series[float] = pa.Field(nullable=True, coerce=True)
    monoisotopic_mass: Series[float] = pa.Field(nullable=True, coerce=True)
    x_steric_quadrupole_3d: Series[float] = pa.Field(nullable=True, coerce=True)
    y_steric_quadrupole_3d: Series[float] = pa.Field(nullable=True, coerce=True)
    z_steric_quadrupole_3d: Series[float] = pa.Field(nullable=True, coerce=True)


__all__ = ["PubChemCompoundGoldSchema"]
