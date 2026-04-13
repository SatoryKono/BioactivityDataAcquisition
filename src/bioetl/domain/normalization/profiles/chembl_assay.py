"""Normalization profile for the ChEMBL Assay Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.schemas.chembl.assay import AssaySchema

__all__ = [
    "CHEMBL_ASSAY_PROFILE",
    "CHEMBL_ASSAY_SCHEMA_FIELDS",
]

CHEMBL_ASSAY_SCHEMA_FIELDS = tuple(AssaySchema.to_schema().columns.keys())

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
_TITLE_FIELDS = frozenset({"assay_pref_name"})
_INT_FIELDS = frozenset({"confidence_score", "src_id"})
_FLOAT_FIELDS = frozenset({"assay_taxonomy_id", "score", "variant_taxonomy_id"})
_JSON_STRING_FIELDS = frozenset(
    {
        "assay_classifications",
        "assay_parameters",
        "variant_sequence_json",
    }
)

CHEMBL_ASSAY_PROFILE = build_standard_profile(
    profile_name="chembl.assay",
    description="Canonical field-level normalization policy for the ChEMBL Assay Silver schema.",
    schema_fields=CHEMBL_ASSAY_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
    float_fields=_FLOAT_FIELDS,
    json_string_fields=_JSON_STRING_FIELDS,
)

CHEMBL_ASSAY_PROFILE.assert_covers_schema(CHEMBL_ASSAY_SCHEMA_FIELDS)
