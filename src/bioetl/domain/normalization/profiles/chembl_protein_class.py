"""Normalization profile for the ChEMBL Protein Class Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._chembl_profile_helpers import (
    ChemblProfileFieldGroups,
    build_chembl_profile,
    chembl_schema_fields,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.normalization.profiles.chembl_policy_registry import (
    chembl_flag_family_fields,
)
from bioetl.domain.schemas.chembl.protein_classification import (
    ProteinClassificationSchema,
)

__all__ = [
    "CHEMBL_PROTEIN_CLASS_PROFILE",
    "CHEMBL_PROTEIN_CLASS_SCHEMA_FIELDS",
]

CHEMBL_PROTEIN_CLASS_SCHEMA_FIELDS = chembl_schema_fields(ProteinClassificationSchema)
_TITLE_FIELDS = frozenset({"pref_name", "short_name"})
_INT_FIELDS = frozenset(
    {
        "protein_class_id",
        "parent_id",
        "replaced_by",
        "class_level",
        "sort_order",
    }
)

CHEMBL_PROTEIN_CLASS_PROFILE = build_chembl_profile(
    entity="protein_class",
    description="Canonical field-level normalization policy for the ChEMBL Protein Class Silver schema.",
    schema_fields=CHEMBL_PROTEIN_CLASS_SCHEMA_FIELDS,
    field_groups=ChemblProfileFieldGroups(
        title_fields=_TITLE_FIELDS,
        int_fields=_INT_FIELDS,
        flag_fields=chembl_flag_family_fields("binary_flags", entity="protein_class"),
        null_fields=chembl_pseudo_null_fields("protein_class"),
    ),
)

CHEMBL_PROTEIN_CLASS_PROFILE.assert_covers_schema(CHEMBL_PROTEIN_CLASS_SCHEMA_FIELDS)
