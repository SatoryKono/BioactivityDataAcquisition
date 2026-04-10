<<<<<<< Updated upstream
"""Normalization profile for the PubChem Compound Silver schema."""

from __future__ import annotations

from ._standard_profile_builder import build_standard_profile
from .helpers import normalize_profile_smiles

__all__ = [
    "PUBCHEM_COMPOUND_PROFILE",
    "PUBCHEM_COMPOUND_SCHEMA_FIELDS",
]

PUBCHEM_COMPOUND_SCHEMA_FIELDS = (
    "entity_id",
    "content_hash",
    "_run_id",
    "_run_type",
    "_source_batch_id",
    "_ingestion_ts",
    "_index",
    "canonical_smiles",
    "molecule_id",
    "complexity",
    "conformer_count_3d",
    "conformer_rmsd_3d",
    "effective_rotor_count_3d",
    "exact_mass",
    "feature_acceptor_count_3d",
    "feature_anion_count_3d",
    "feature_cation_count_3d",
    "feature_count_3d",
    "feature_donor_count_3d",
    "feature_hydrophobe_count_3d",
    "feature_ring_count_3d",
    "inchi",
    "inchi_key",
    "isomeric_smiles",
    "iupac_name",
    "molecular_formula",
    "molecular_weight",
    "monoisotopic_mass",
    "tpsa",
    "x_steric_quadrupole_3d",
    "xlogp",
    "y_steric_quadrupole_3d",
    "z_steric_quadrupole_3d",
    "_dq_error",
    "_dq_warn",
)

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
_FLOAT_FIELDS = frozenset(
    {
        "complexity",
        "conformer_count_3d",
        "conformer_rmsd_3d",
        "effective_rotor_count_3d",
        "exact_mass",
        "feature_acceptor_count_3d",
        "feature_anion_count_3d",
        "feature_cation_count_3d",
        "feature_count_3d",
        "feature_donor_count_3d",
        "feature_hydrophobe_count_3d",
        "feature_ring_count_3d",
        "molecular_weight",
        "monoisotopic_mass",
        "tpsa",
        "x_steric_quadrupole_3d",
        "xlogp",
        "y_steric_quadrupole_3d",
        "z_steric_quadrupole_3d",
    }
)
_SPECIAL_RULES = {
    "canonical_smiles": (
        lambda value: normalize_profile_smiles(value, is_canonical=True),
        "Normalize canonical SMILES via the domain SMILES Value Object; invalid values collapse to None.",
    ),
    "isomeric_smiles": (
        lambda value: normalize_profile_smiles(value, is_canonical=False),
        "Normalize isomeric SMILES via the domain SMILES Value Object; invalid values collapse to None.",
    ),
}

PUBCHEM_COMPOUND_PROFILE = build_standard_profile(
    profile_name="pubchem.compound",
    description="Canonical field-level normalization policy for the PubChem Compound Silver schema.",
    schema_fields=PUBCHEM_COMPOUND_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    float_fields=_FLOAT_FIELDS,
    special_rules=_SPECIAL_RULES,
)

PUBCHEM_COMPOUND_PROFILE.assert_covers_schema(PUBCHEM_COMPOUND_SCHEMA_FIELDS)
||||||| Stash base
=======
"""Normalization profile for the PubChem Compound Silver schema."""

from __future__ import annotations

from bioetl.infrastructure.schemas.silver_compounds import PUBCHEM_COMPOUND_SCHEMA

from ._standard_profile_builder import build_standard_profile
from .helpers import normalize_profile_smiles

__all__ = [
    "PUBCHEM_COMPOUND_PROFILE",
    "PUBCHEM_COMPOUND_SCHEMA_FIELDS",
]

PUBCHEM_COMPOUND_SCHEMA_FIELDS = tuple(PUBCHEM_COMPOUND_SCHEMA.names)

_META_FIELDS = frozenset(
    field_name for field_name in PUBCHEM_COMPOUND_SCHEMA_FIELDS if field_name.startswith("_")
) | {"content_hash", "entity_id"}

_FLOAT_FIELDS = frozenset(
    {
        "complexity",
        "conformer_count_3d",
        "conformer_rmsd_3d",
        "effective_rotor_count_3d",
        "exact_mass",
        "feature_acceptor_count_3d",
        "feature_anion_count_3d",
        "feature_cation_count_3d",
        "feature_count_3d",
        "feature_donor_count_3d",
        "feature_hydrophobe_count_3d",
        "feature_ring_count_3d",
        "molecular_weight",
        "monoisotopic_mass",
        "tpsa",
        "x_steric_quadrupole_3d",
        "xlogp",
        "y_steric_quadrupole_3d",
        "z_steric_quadrupole_3d",
    }
)


def _normalize_canonical_smiles(value: object) -> object:
    return normalize_profile_smiles(value, is_canonical=True)


def _normalize_isomeric_smiles(value: object) -> object:
    return normalize_profile_smiles(value, is_canonical=False)


PUBCHEM_COMPOUND_PROFILE = build_standard_profile(
    profile_name="pubchem.compound",
    description="Canonical normalization profile for the PubChem Compound Silver schema.",
    schema_fields=PUBCHEM_COMPOUND_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    float_fields=_FLOAT_FIELDS,
    special_rules={
        "canonical_smiles": (
            _normalize_canonical_smiles,
            "Normalize canonical SMILES via the domain SMILES Value Object; invalid values collapse to None.",
        ),
        "isomeric_smiles": (
            _normalize_isomeric_smiles,
            "Normalize isomeric SMILES via the domain SMILES Value Object; invalid values collapse to None.",
        ),
    },
)

PUBCHEM_COMPOUND_PROFILE.assert_covers_schema(PUBCHEM_COMPOUND_SCHEMA_FIELDS)
>>>>>>> Stashed changes
