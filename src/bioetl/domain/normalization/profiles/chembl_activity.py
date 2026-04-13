"""Normalization profile for the ChEMBL Activity Silver schema."""

from __future__ import annotations

from ._chembl_activity_fields import (
    CHEMBL_ACTIVITY_SCHEMA_FIELDS,
    FLOAT_FIELDS,
    INT_FIELDS,
    META_FIELDS,
    SET_LIKE_FIELDS,
)
from ._standard_profile_builder import build_standard_profile
from .profile_normalizers import normalize_profile_canonical_smiles

__all__ = [
    "CHEMBL_ACTIVITY_PROFILE",
    "CHEMBL_ACTIVITY_SCHEMA_FIELDS",
]

_SPECIAL_RULE_COMPONENTS = {
    "canonical_smiles": (
        normalize_profile_canonical_smiles,
        "Normalize canonical SMILES via the domain SMILES Value Object; invalid values collapse to None.",
    ),
}


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
    special_rules=_SPECIAL_RULE_COMPONENTS,
)

CHEMBL_ACTIVITY_PROFILE.assert_covers_schema(CHEMBL_ACTIVITY_SCHEMA_FIELDS)
