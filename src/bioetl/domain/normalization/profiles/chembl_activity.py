"""Normalization profile for the ChEMBL Activity Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.rules import normalize_cross_pipeline_case

from ._chembl_activity_fields import (
    ACTIVITY_STANDARD_TYPES,
    ACTIVITY_STANDARD_UNITS,
    CHEMBL_ACTIVITY_SCHEMA_FIELDS,
    DATA_VALIDITY_COMMENTS,
    FLOAT_FIELDS,
    INT_FIELDS,
    META_FIELDS,
    SET_LIKE_FIELDS,
    STANDARD_RELATIONS,
)
from ._standard_profile_builder import build_standard_profile
from .chembl_pseudo_nulls import chembl_pseudo_null_fields
from .profile_normalizers import (
    normalize_profile_bao_identifier,
    normalize_profile_canonical_smiles,
    normalize_profile_enum,
    normalize_profile_operator,
)

__all__ = [
    "ACTIVITY_STANDARD_TYPES",
    "ACTIVITY_STANDARD_UNITS",
    "ASSAY_TYPES",
    "CHEMBL_ACTIVITY_PROFILE",
    "CHEMBL_ACTIVITY_SCHEMA_FIELDS",
    "DATA_VALIDITY_COMMENTS",
    "NULL_FIELDS",
    "STANDARD_RELATIONS",
]

# Assay types enum (B, F, A, T, P, U)
ASSAY_TYPES = frozenset(["B", "F", "A", "T", "P", "U"])


def create_case_normalizer(strategy: str = "uppercase"):
    """Create a case normalizer function for profile use.

    Args:
        strategy: Case strategy ("uppercase", "lowercase", or "preserve")

    Returns:
        Normalizer function suitable for profile special_rules
    """

    def normalizer(value):
        return normalize_cross_pipeline_case(value, strategy)

    return normalizer


# Enum fields for strict validation
_ENUM_FIELDS = {
    "standard_relation": STANDARD_RELATIONS,
    "standard_type": ACTIVITY_STANDARD_TYPES,
    "assay_type": ASSAY_TYPES,
}
_ONTOLOGY_ID_FIELDS = frozenset({"uo_units"})
_UNIT_FIELDS = frozenset({"standard_units", "qudt_units"})

_SPECIAL_RULE_COMPONENTS = {
    "canonical_smiles": (
        normalize_profile_canonical_smiles,
        "Normalize canonical SMILES via the domain SMILES Value Object; invalid values collapse to None.",
    ),
    "standard_relation": (
        lambda value: normalize_profile_operator(
            value,
            allowed_values=STANDARD_RELATIONS,
        ),
        "Normalize standard_relation to a canonical ASCII operator enum.",
    ),
    "assay_type": (
        lambda value: normalize_profile_enum(value, allowed_values=ASSAY_TYPES),
        "Normalize assay_type to uppercase enum value and collapse unknown values to None.",
    ),
    "bao_endpoint": (
        normalize_profile_bao_identifier,
        "Normalize BAO endpoint identifier to canonical BAO underscore form.",
    ),
    "bao_format": (
        normalize_profile_bao_identifier,
        "Normalize BAO format identifier to canonical BAO underscore form.",
    ),
}


NULL_FIELDS = chembl_pseudo_null_fields("activity")

CHEMBL_ACTIVITY_PROFILE = build_standard_profile(
    profile_name="chembl.activity",
    description=(
        "Canonical field-level normalization policy for the ChEMBL Activity Silver schema."
    ),
    schema_fields=CHEMBL_ACTIVITY_SCHEMA_FIELDS,
    meta_fields=META_FIELDS,
    doi_fields={"publication_doi"},
    pmid_fields={"publication_pmid"},
    pmc_id_fields={"publication_pmc_id"},
    int_fields=INT_FIELDS,
    float_fields=FLOAT_FIELDS,
    flag_fields={"standard_flag", "potential_duplicate", "manual_curation_flag"},
    operator_fields={"relation"},
    set_like_fields=SET_LIKE_FIELDS,
    ontology_id_fields=_ONTOLOGY_ID_FIELDS,
    enum_fields={
        "standard_relation": STANDARD_RELATIONS,
        "standard_type": ACTIVITY_STANDARD_TYPES,
        "assay_type": ASSAY_TYPES,
        "data_validity_comment": DATA_VALIDITY_COMMENTS,
    },
    special_rules=_SPECIAL_RULE_COMPONENTS,
    unit_fields=_UNIT_FIELDS,
    null_fields=NULL_FIELDS,
)

CHEMBL_ACTIVITY_PROFILE.assert_covers_schema(CHEMBL_ACTIVITY_SCHEMA_FIELDS)
