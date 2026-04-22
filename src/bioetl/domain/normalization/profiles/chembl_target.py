"""Normalization profile for the ChEMBL Target Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.constants import TARGET_TYPES

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
_FLOAT_FIELDS = frozenset({"primary_component_id", "taxonomy_id"})
_BOOLEAN_FIELDS = frozenset({"species_group_flag", "downgraded"})
_JSON_STRING_FIELDS = frozenset(
    {
        "target_components",
        "cross_references",
        "pipeline_stages",
        "target_component_synonyms",
        "component_accessions",
        "component_descriptions",
        "component_ids",
        "component_types",
        "component_relationships",
    }
)
_NULL_FIELDS = frozenset({"description", "organism_class", "component_relationships"})

# Enum fields for strict validation
_ENUM_FIELDS = {
    "target_type": TARGET_TYPES,
}

CHEMBL_TARGET_PROFILE = build_standard_profile(
    profile_name="chembl.target",
    description="Canonical field-level normalization policy for the ChEMBL Target Silver schema.",
    schema_fields=CHEMBL_TARGET_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    float_fields=_FLOAT_FIELDS,
    boolean_fields=_BOOLEAN_FIELDS,
    json_string_fields=_JSON_STRING_FIELDS,
    enum_fields=_ENUM_FIELDS,
    null_fields=_NULL_FIELDS,
)

CHEMBL_TARGET_PROFILE.assert_covers_schema(CHEMBL_TARGET_SCHEMA_FIELDS)
