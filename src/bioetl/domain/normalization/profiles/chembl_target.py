"""Normalization profile for the ChEMBL Target Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.infrastructure.schemas.silver_chembl import CHEMBL_TARGET_SCHEMA

__all__ = [
    "CHEMBL_TARGET_PROFILE",
    "CHEMBL_TARGET_SCHEMA_FIELDS",
]

CHEMBL_TARGET_SCHEMA_FIELDS = tuple(CHEMBL_TARGET_SCHEMA.names)

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

CHEMBL_TARGET_PROFILE = build_standard_profile(
    profile_name="chembl.target",
    description="Canonical field-level normalization policy for the ChEMBL Target Silver schema.",
    schema_fields=CHEMBL_TARGET_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    float_fields=_FLOAT_FIELDS,
)

CHEMBL_TARGET_PROFILE.assert_covers_schema(CHEMBL_TARGET_SCHEMA_FIELDS)
