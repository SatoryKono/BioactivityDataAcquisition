"""Normalization profile for the ChEMBL Assay Parameters Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.schemas.chembl.assay_parameters import AssayParametersSchema

__all__ = [
    "CHEMBL_ASSAY_PARAMETERS_PROFILE",
    "CHEMBL_ASSAY_PARAMETERS_SCHEMA_FIELDS",
]

CHEMBL_ASSAY_PARAMETERS_SCHEMA_FIELDS = tuple(
    AssayParametersSchema.to_schema().columns.keys()
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
_INT_FIELDS = frozenset({"assay_param_id"})
_FLOAT_FIELDS = frozenset({"standard_value", "value"})
_JSON_STRING_FIELDS = frozenset({"comments"})

CHEMBL_ASSAY_PARAMETERS_PROFILE = build_standard_profile(
    profile_name="chembl.assay_parameters",
    description="Canonical field-level normalization policy for the ChEMBL Assay Parameters Silver schema.",
    schema_fields=CHEMBL_ASSAY_PARAMETERS_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    int_fields=_INT_FIELDS,
    float_fields=_FLOAT_FIELDS,
    json_string_fields=_JSON_STRING_FIELDS,
    null_fields=chembl_pseudo_null_fields("assay_parameters"),
)

CHEMBL_ASSAY_PARAMETERS_PROFILE.assert_covers_schema(
    CHEMBL_ASSAY_PARAMETERS_SCHEMA_FIELDS
)
