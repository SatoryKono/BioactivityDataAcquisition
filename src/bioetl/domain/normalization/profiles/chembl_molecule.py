"""Normalization profile for the ChEMBL Molecule Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._chembl_policy_registry import (
    chembl_boolean_family_fields,
    chembl_flag_family_fields,
)
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_canonical_smiles,
    normalize_profile_quasi_enum_numeric,
    normalize_profile_reviewed_flag_code,
)
from bioetl.domain.schemas.chembl.molecule import MoleculeSchema
from bioetl.domain.schemas.constants import (
    MAX_PHASE_VALUES,
    MOLECULE_TYPES,
    STRUCTURE_TYPES,
)

from ._chembl_vocab import chembl_enum
from .chembl_json_ordering_policy import chembl_json_fields

__all__ = [
    "CHEMBL_MOLECULE_PROFILE",
    "CHEMBL_MOLECULE_SCHEMA_FIELDS",
]

CHEMBL_MOLECULE_SCHEMA_FIELDS = tuple(MoleculeSchema.to_schema().columns.keys())
RO3_PASS_VALUES = chembl_enum("molecule", "ro3_pass")

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
        "polymer_flag",
        "aromatic_ring_count",
        "hba_count",
        "hbd_count",
        "heavy_atom_count",
        "ro5_violation_count",
        "rotatable_bond_count",
    }
)
_BOOLEAN_FIELDS = chembl_boolean_family_fields("bool_like", entity="molecule")
_FLAG_FIELDS = chembl_flag_family_fields("binary_flags", entity="molecule")
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
_STRICT_JSON_FIELDS = chembl_json_fields("chembl_molecule")
_NULL_FIELDS = chembl_pseudo_null_fields("molecule")

_SPECIAL_RULES = {
    "canonical_smiles": (
        normalize_profile_canonical_smiles,
        "Normalize canonical SMILES via the domain SMILES Value Object; invalid values collapse to None.",
    ),
    "max_phase": (
        lambda value: normalize_profile_quasi_enum_numeric(
            value,
            allowed_values=MAX_PHASE_VALUES,
        ),
        "Normalize max_phase as a reviewed quasi-enum numeric provider code; "
        "preserve canonical values including 0.5 and collapse out-of-universe "
        "inputs to None.",
    ),
    "first_in_class": (
        normalize_profile_reviewed_flag_code,
        "Normalize first_in_class as a reviewed flag-like provider code with "
        "the canonical tri-state universe {-1, 0, 1}.",
    ),
    "inorganic_flag": (
        normalize_profile_reviewed_flag_code,
        "Normalize inorganic_flag as a reviewed flag-like provider code with "
        "the canonical tri-state universe {-1, 0, 1}.",
    ),
    "natural_product": (
        normalize_profile_reviewed_flag_code,
        "Normalize natural_product as a reviewed flag-like provider code with "
        "the canonical tri-state universe {-1, 0, 1}.",
    ),
    "prodrug": (
        normalize_profile_reviewed_flag_code,
        "Normalize prodrug as a reviewed flag-like provider code with the "
        "canonical tri-state universe {-1, 0, 1}.",
    ),
}

# Enum fields for strict validation
_ENUM_FIELDS = {
    "molecule_type": MOLECULE_TYPES,
    "structure_type": STRUCTURE_TYPES,
    "ro3_pass": RO3_PASS_VALUES,
}

CHEMBL_MOLECULE_PROFILE = build_standard_profile(
    profile_name="chembl.molecule",
    description=(
        "Canonical field-level normalization policy for the ChEMBL Molecule "
        "Silver schema."
    ),
    schema_fields=CHEMBL_MOLECULE_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
    float_fields=_FLOAT_FIELDS,
    boolean_fields=_BOOLEAN_FIELDS,
    flag_fields=_FLAG_FIELDS,
    strict_json_fields=_STRICT_JSON_FIELDS,
    enum_fields=_ENUM_FIELDS,
    special_rules=_SPECIAL_RULES,
    null_fields=_NULL_FIELDS,
)

CHEMBL_MOLECULE_PROFILE.assert_covers_schema(CHEMBL_MOLECULE_SCHEMA_FIELDS)
