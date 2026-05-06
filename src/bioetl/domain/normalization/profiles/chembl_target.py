"""Normalization profile for the ChEMBL Target Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._chembl_policy_registry import (
    chembl_boolean_family_fields,
)
from bioetl.domain.normalization.profiles._chembl_reference_identifier_rules import (
    chembl_reference_identifier_rules,
)
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_chembl_organism_name,
    normalize_profile_target_component_relationships,
    normalize_profile_target_component_types,
)
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.constants import TARGET_TYPES

from .chembl_json_ordering_policy import (
    chembl_json_fields,
    chembl_set_like_json_fields,
)

__all__ = [
    "CHEMBL_TARGET_PROFILE",
    "CHEMBL_TARGET_SCHEMA_FIELDS",
]

CHEMBL_TARGET_SCHEMA_FIELDS = tuple(TargetSchema.to_schema().columns.keys())

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
_INT_FIELDS = frozenset({"taxonomy_id"})
_FLOAT_FIELDS = frozenset({"primary_component_id"})
_BOOLEAN_FIELDS = chembl_boolean_family_fields("bool_like", entity="target")
_SET_LIKE_FIELDS = chembl_set_like_json_fields("chembl_target")
_STRICT_JSON_FIELDS = chembl_json_fields("chembl_target")
_NULL_FIELDS = chembl_pseudo_null_fields("target")
_REFERENCE_IDENTIFIER_RULES = chembl_reference_identifier_rules("target")

# Enum fields for strict validation
_ENUM_FIELDS = {
    "target_type": TARGET_TYPES,
}
_SPECIAL_RULE_COMPONENTS = {
    **_REFERENCE_IDENTIFIER_RULES,
    "organism": (
        normalize_profile_chembl_organism_name,
        "Normalize ChEMBL target organism display name using curated organism aliases.",
    ),
    "component_types": (
        normalize_profile_target_component_types,
        "Normalize target component_types as a canonical JSON array with "
        "element-wise validation against the shared ChEMBL "
        "target-component type registry.",
    ),
    "component_relationships": (
        normalize_profile_target_component_relationships,
        "Normalize target component_relationships as a canonical JSON array "
        "with element-wise validation against the shared ChEMBL "
        "target-component relationship registry.",
    ),
}

CHEMBL_TARGET_PROFILE = build_standard_profile(
    profile_name="chembl.target",
    description="Canonical field-level normalization policy for the ChEMBL Target Silver schema.",
    schema_fields=CHEMBL_TARGET_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
    float_fields=_FLOAT_FIELDS,
    set_like_fields=_SET_LIKE_FIELDS,
    boolean_fields=_BOOLEAN_FIELDS,
    strict_json_fields=_STRICT_JSON_FIELDS,
    enum_fields=_ENUM_FIELDS,
    special_rules=_SPECIAL_RULE_COMPONENTS,
    null_fields=_NULL_FIELDS,
)

CHEMBL_TARGET_PROFILE.assert_covers_schema(CHEMBL_TARGET_SCHEMA_FIELDS)
