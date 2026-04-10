"""Normalization profile for the ChEMBL Molecule Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.helpers import normalize_profile_smiles
from bioetl.domain.schemas.chembl.molecule import MoleculeSchema

__all__ = [
    "CHEMBL_MOLECULE_PROFILE",
    "CHEMBL_MOLECULE_SCHEMA_FIELDS",
]

CHEMBL_MOLECULE_SCHEMA_FIELDS = tuple(MoleculeSchema.to_schema().columns.keys())

_META_FIELDS = frozenset(
    {
        "entity_id",
        "content_hash",
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_ingestion_ts",
        "_index",
        "_dq_error",
        "_dq_warn",
    }
)
_TITLE_FIELDS = frozenset({"pref_name"})
_INT_FIELDS = frozenset(
    {
        "black_box_warning",
        "chirality",
        "dosed_ingredient",
        "first_in_class",
        "inorganic_flag",
        "max_phase",
        "natural_product",
        "polymer_flag",
        "prodrug",
        "aromatic_ring_count",
        "hba_count",
        "hbd_count",
        "heavy_atom_count",
        "ro5_violation_count",
        "rotatable_bond_count",
    }
)
_FLOAT_FIELDS = frozenset(
    {
        "availability_type",
        "first_approval",
        "logp",
        "molecular_weight",
        "mw_freebase",
        "polar_surface_area",
        "qed_score",
        "usan_year",
    }
)


def _normalize_canonical_smiles(value: object) -> object:
    return normalize_profile_smiles(value, is_canonical=True)


_SPECIAL_RULES = {
    "canonical_smiles": (
        _normalize_canonical_smiles,
        "Normalize canonical SMILES via the domain SMILES Value Object; invalid values collapse to None.",
    ),
}

CHEMBL_MOLECULE_PROFILE = build_standard_profile(
    profile_name="chembl.molecule",
    description="Canonical field-level normalization policy for the ChEMBL Molecule Silver schema.",
    schema_fields=CHEMBL_MOLECULE_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
    float_fields=_FLOAT_FIELDS,
    special_rules=_SPECIAL_RULES,
)

CHEMBL_MOLECULE_PROFILE.assert_covers_schema(CHEMBL_MOLECULE_SCHEMA_FIELDS)
