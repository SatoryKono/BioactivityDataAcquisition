"""Normalization profile for the PubChem Compound Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.chemical_standardization_contract import (
    CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    CHEMICAL_STANDARDIZATION_STATUSES,
)
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_canonical_smiles,
    normalize_profile_inchi_key,
    normalize_profile_isomeric_smiles,
)
from bioetl.domain.schemas.pubchem.compound import PubchemMoleculeSchema

__all__ = [
    "PUBCHEM_COMPOUND_PROFILE",
    "PUBCHEM_COMPOUND_SCHEMA_FIELDS",
]

PUBCHEM_COMPOUND_SCHEMA_FIELDS = tuple(PubchemMoleculeSchema.to_schema().columns.keys())

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
_ENUM_FIELDS = {
    "chemical_standardization_policy_version": frozenset(
        {CHEMICAL_STANDARDIZATION_POLICY_VERSION}
    ),
    "chemical_standardization_status": frozenset(CHEMICAL_STANDARDIZATION_STATUSES),
}

_SPECIAL_RULES = {
    "canonical_smiles": (
        normalize_profile_canonical_smiles,
        "Normalize canonical SMILES via the domain SMILES Value Object; invalid values collapse to None.",
    ),
    "inchi_key": (
        normalize_profile_inchi_key,
        "Validate InChIKey through the canonical domain value-object contract, then emit uppercase canonical text.",
    ),
    "isomeric_smiles": (
        normalize_profile_isomeric_smiles,
        "Normalize isomeric SMILES via the domain SMILES Value Object; invalid values collapse to None.",
    ),
    "standardized_inchi_key": (
        normalize_profile_inchi_key,
        "Validate standardized InChIKey through the canonical domain value-object contract, then emit uppercase canonical text.",
    ),
}

PUBCHEM_COMPOUND_PROFILE = build_standard_profile(
    profile_name="pubchem.compound",
    description="Canonical field-level normalization policy for the PubChem Compound Silver schema.",
    schema_fields=PUBCHEM_COMPOUND_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    float_fields=_FLOAT_FIELDS,
    enum_fields=_ENUM_FIELDS,
    special_rules=_SPECIAL_RULES,
)

PUBCHEM_COMPOUND_PROFILE.assert_covers_schema(PUBCHEM_COMPOUND_SCHEMA_FIELDS)
