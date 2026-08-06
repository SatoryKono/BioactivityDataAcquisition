# mypy: disable-error-code="misc"
"""ChEMBL molecule/protein-class Gold-layer contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold._strict_gold_contract_schema import (
    CONTENT_HASH_HEX64_PATTERN,
    StrictGoldContractSchema,
)


class ChEMBLMoleculeGoldSchema(StrictGoldContractSchema):
    """Schema for ChEMBL Molecule in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(
        nullable=False,
        str_matches=CONTENT_HASH_HEX64_PATTERN,
    )
    molecule_id: Series[str] = pa.Field(nullable=False)
    pref_name: Series[str] = pa.Field(nullable=True)
    molecule_type: Series[str] = pa.Field(nullable=True)
    structure_type: Series[str] = pa.Field(nullable=True)
    max_phase: Series[float] = pa.Field(nullable=True, coerce=True)
    first_approval: Series[float] = pa.Field(nullable=True, coerce=True)
    chirality: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    dosed_ingredient: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    availability_type: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    usan_stem: Series[str] = pa.Field(nullable=True)
    usan_stem_definition: Series[str] = pa.Field(nullable=True)
    usan_substem: Series[str] = pa.Field(nullable=True)
    usan_year: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    helm_notation: Series[str] = pa.Field(nullable=True)
    molecule_species: Series[str] = pa.Field(nullable=True)
    oral: Series[bool] = pa.Field(nullable=True, coerce=True)
    parenteral: Series[bool] = pa.Field(nullable=True, coerce=True)
    topical: Series[bool] = pa.Field(nullable=True, coerce=True)
    black_box_warning: Series[float] = pa.Field(nullable=True, coerce=True)
    natural_product: Series[float] = pa.Field(nullable=True, coerce=True)
    first_in_class: Series[float] = pa.Field(nullable=True, coerce=True)
    prodrug: Series[float] = pa.Field(nullable=True, coerce=True)
    therapeutic_flag: Series[bool] = pa.Field(nullable=True, coerce=True)
    withdrawn_flag: Series[bool] = pa.Field(nullable=True, coerce=True)
    inorganic_flag: Series[float] = pa.Field(nullable=True, coerce=True)
    polymer_flag: Series[float] = pa.Field(nullable=True, coerce=True)
    molecule_hierarchy: Series[str] = pa.Field(nullable=True)
    molecule_properties: Series[str] = pa.Field(nullable=True)
    molecule_structures: Series[str] = pa.Field(nullable=True)
    molecule_synonyms: Series[str] = pa.Field(nullable=True)
    cross_references: Series[str] = pa.Field(nullable=True)
    atc_classifications: Series[str] = pa.Field(nullable=True)
    hierarchy_parent_chembl_id: Series[str] = pa.Field(nullable=True)
    hierarchy_active_chembl_id: Series[str] = pa.Field(nullable=True)
    hierarchy_child_chembl_id: Series[str] = pa.Field(nullable=True)
    logp: Series[float] = pa.Field(nullable=True, coerce=True)
    logp_method: Series[str] = pa.Field(nullable=True)
    molecular_weight: Series[float] = pa.Field(nullable=True, coerce=True)
    mw_freebase: Series[float] = pa.Field(nullable=True, coerce=True)
    polar_surface_area: Series[float] = pa.Field(nullable=True, coerce=True)
    rotatable_bond_count: Series[float] = pa.Field(nullable=True, coerce=True)
    ro5_violation_count: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    heavy_atom_count: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    aromatic_ring_count: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    hba_count: Series[float] = pa.Field(nullable=True, coerce=True)
    hbd_count: Series[float] = pa.Field(nullable=True, coerce=True)
    qed_score: Series[float] = pa.Field(nullable=True, coerce=True)
    molecular_formula: Series[str] = pa.Field(nullable=True)
    ro3_pass: Series[str] = pa.Field(nullable=True)
    # Flattened Structures (unified naming without structure_ prefix)
    canonical_smiles: Series[str] = pa.Field(nullable=True)
    standard_inchi: Series[str] = pa.Field(nullable=True)
    inchi_key: Series[str] = pa.Field(nullable=True)


class ChEMBLProteinClassGoldSchema(StrictGoldContractSchema):
    """Schema for ChEMBL Protein Classification in Gold layer.

    Hierarchical classification of protein targets (enzyme classes, receptor types, etc.).
    Self-referencing structure with up to 8 levels of depth.
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(
        nullable=False,
        str_matches=CONTENT_HASH_HEX64_PATTERN,
    )

    # Primary identifier
    protein_class_id: Series[float] = pa.Field(nullable=False, ge=1, coerce=True)

    # Hierarchy
    parent_id: Series[float] = pa.Field(nullable=True, ge=1, coerce=True)
    class_level: Series[float] = pa.Field(nullable=True, ge=1, le=8, coerce=True)

    # Classification data
    pref_name: Series[str] = pa.Field(nullable=True)
    short_name: Series[str] = pa.Field(nullable=True)
    protein_class_desc: Series[str] = pa.Field(nullable=True)
    definition: Series[str] = pa.Field(nullable=True)

    # Additional metadata
    sort_order: Series[float] = pa.Field(nullable=True, coerce=True)
    replaced_by: Series[float] = pa.Field(nullable=True, ge=1, coerce=True)
    downgraded: Series[float] = pa.Field(nullable=True, isin=[0, 1], coerce=True)


__all__ = [
    "ChEMBLMoleculeGoldSchema",
    "ChEMBLProteinClassGoldSchema",
]
