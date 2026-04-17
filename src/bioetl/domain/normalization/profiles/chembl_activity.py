"""Normalization profile for the ChEMBL Activity Silver schema."""

from __future__ import annotations

from ._chembl_activity_fields import (
    ACTIVITY_STANDARD_TYPES,
    CHEMBL_ACTIVITY_SCHEMA_FIELDS,
    DATA_VALIDITY_COMMENTS,
    FLOAT_FIELDS,
    INT_FIELDS,
    META_FIELDS,
    SET_LIKE_FIELDS,
    STANDARD_RELATIONS,
)
from .profile_normalizers import normalize_profile_case, normalize_profile_unit
from bioetl.domain.normalization.rules import normalize_cross_pipeline_case
from bioetl.domain.normalization.identifiers import normalize_ontology_id
from ._standard_profile_builder import build_standard_profile
from .profile_normalizers import normalize_profile_canonical_smiles

__all__ = [
    "ASSAY_TYPES",
    "CHEMBL_ACTIVITY_PROFILE",
    "CHEMBL_ACTIVITY_SCHEMA_FIELDS",
    "NULL_FIELDS",
    "STANDARD_RELATIONS",
    "ACTIVITY_STANDARD_TYPES",
    "DATA_VALIDITY_COMMENTS",
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

_SPECIAL_RULE_COMPONENTS = {
    "canonical_smiles": (
        normalize_profile_canonical_smiles,
        "Normalize canonical SMILES via the domain SMILES Value Object; invalid values collapse to None.",
    ),
    "bao_format": (
        normalize_ontology_id,
        "Normalize BAO ontology ID to underscore format (e.g., 'BAO:0000190' -> 'BAO_0000190').",
    ),
    "assay_type": (
        create_case_normalizer("uppercase"),
        "Normalize assay_type to uppercase enum value.",
    ),
    "assay_test_type": (
        create_case_normalizer("preserve"),
        "Normalize assay_test_type preserving original case (e.g., 'In vivo').",
    ),
    "assay_category": (
        create_case_normalizer("preserve"),
        "Normalize assay_category preserving original case.",
    ),
}


# Fields that commonly contain pseudo-null values and should be normalized
NULL_FIELDS = frozenset(
    [
        "standard_value",
        "value",
        "upper_value",
        "standard_upper_value",
        "pchembl_value",
        "data_validity_comment",
        "assay_description",
        "target_relation",
        "target_organism",
        "target_taxonomy",
        "cell_line",
        "tissue",
        "assay_type",
        "assay_test_type",
        "assay_category",
        "bao_format",
        "bao_label",
        "bao_endpoint",
    ]
)

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
    set_like_fields=SET_LIKE_FIELDS,
    enum_fields={
        "standard_relation": STANDARD_RELATIONS,
        "standard_type": ACTIVITY_STANDARD_TYPES,
        "data_validity_comment": DATA_VALIDITY_COMMENTS,
    },
    special_rules=_SPECIAL_RULE_COMPONENTS,
    unit_fields={"standard_units"},
    null_fields=NULL_FIELDS,
)

CHEMBL_ACTIVITY_PROFILE.assert_covers_schema(CHEMBL_ACTIVITY_SCHEMA_FIELDS)
