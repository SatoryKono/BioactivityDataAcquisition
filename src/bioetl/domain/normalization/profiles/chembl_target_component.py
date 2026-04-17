"""Normalization profile for the ChEMBL Target Component Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.schemas.chembl.target_component import TargetComponentSchema

__all__ = [
    "CHEMBL_TARGET_COMPONENT_PROFILE",
    "CHEMBL_TARGET_COMPONENT_SCHEMA_FIELDS",
]

CHEMBL_TARGET_COMPONENT_SCHEMA_FIELDS = tuple(
    TargetComponentSchema.to_schema().columns.keys()
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
_INT_FIELDS = frozenset({"component_id", "taxonomy_id", "protein_classification_id"})
_JSON_STRING_FIELDS = frozenset(
    {"protein_classification_ids", "target_component_xrefs"}
)

CHEMBL_TARGET_COMPONENT_PROFILE = build_standard_profile(
    profile_name="chembl.target_component",
    description="Canonical field-level normalization policy for the ChEMBL Target Component Silver schema.",
    schema_fields=CHEMBL_TARGET_COMPONENT_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    int_fields=_INT_FIELDS,
    json_string_fields=_JSON_STRING_FIELDS,
)

CHEMBL_TARGET_COMPONENT_PROFILE.assert_covers_schema(
    CHEMBL_TARGET_COMPONENT_SCHEMA_FIELDS
)
