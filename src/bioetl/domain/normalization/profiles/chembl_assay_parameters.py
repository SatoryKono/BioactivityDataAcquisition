"""Normalization profile for the ChEMBL Assay Parameters Silver schema."""

from __future__ import annotations

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
    normalize_profile_assay_parameter_type,
    normalize_profile_operator,
    normalize_profile_standard_unit_enum,
    normalize_profile_text,
)
from bioetl.domain.schemas.chembl.assay_parameters import AssayParametersSchema

from ._chembl_policy_registry import chembl_controlled_family_fields
from ._chembl_vocab import chembl_enum

__all__ = [
    "CHEMBL_ASSAY_PARAMETERS_PROFILE",
    "CHEMBL_ASSAY_PARAMETERS_SCHEMA_FIELDS",
]

CHEMBL_ASSAY_PARAMETERS_SCHEMA_FIELDS = tuple(
    AssayParametersSchema.to_schema().columns.keys()
)
ASSAY_PARAMETER_STANDARD_TYPES = chembl_enum("assay_parameters", "standard_type")
ASSAY_PARAMETER_STANDARD_UNITS = chembl_enum("activity", "standard_units")
STANDARD_RELATIONS = chembl_enum("assay_parameters", "standard_relation")

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
_OPERATOR_FIELDS = chembl_controlled_family_fields(
    "operators", entity="assay_parameters"
)
_RAW_UNIT_FIELDS = chembl_controlled_family_fields(
    "raw_units", entity="assay_parameters"
)
_TYPE_FIELDS = chembl_controlled_family_fields(
    "assay_parameter_types",
    entity="assay_parameters",
)
_REFERENCE_IDENTIFIER_RULES = chembl_reference_identifier_rules("assay_parameters")


def normalize_assay_parameter_standard_units(value: object) -> object:
    """Normalize one assay-parameter standard-unit field against the strict enum."""
    return normalize_profile_standard_unit_enum(
        value,
        allowed_values=ASSAY_PARAMETER_STANDARD_UNITS,
    )


def normalize_profile_assay_parameter_type_field(value: object) -> object:
    return normalize_profile_assay_parameter_type(
        value,
        allowed_values=ASSAY_PARAMETER_STANDARD_TYPES,
    )


_TYPE_RULE = (
    normalize_profile_assay_parameter_type_field,
    (
        "Normalize assay-parameter type as an explicit controlled-vocabulary surface against the shared "
        "registry, while preserving unknown provider lexemes as uppercase "
        "for explicit raw-vs-canonical review without rejecting unknown."
    ),
)


_SPECIAL_RULE_COMPONENTS = {
    **_REFERENCE_IDENTIFIER_RULES,
    "type_raw": (
        normalize_profile_text,
        "Preserve the raw assay-parameter type provider lexeme as trimmed text "
        "before canonical controlled-vocabulary normalization.",
    ),
    "comments": (
        normalize_profile_text,
        "Normalize assay parameter comments as plain text; comments are not JSON-canonicalized by default.",
    ),
    "standard_relation": (
        lambda value: normalize_profile_operator(
            value,
            allowed_values=STANDARD_RELATIONS,
        ),
        "Normalize standard_relation to a canonical ASCII operator enum.",
    ),
    "standard_units": (
        normalize_assay_parameter_standard_units,
        "Normalize assay-parameter standard_units against the "
        "published ChEMBL standard-unit enum after canonical unit "
        "alias collapse; unknown values collapse to None.",
    ),
    **dict.fromkeys(sorted(_TYPE_FIELDS), _TYPE_RULE),
}

CHEMBL_ASSAY_PARAMETERS_PROFILE = build_standard_profile(
    profile_name="chembl.assay_parameters",
    description="Canonical field-level normalization policy for the ChEMBL Assay Parameters Silver schema.",
    schema_fields=CHEMBL_ASSAY_PARAMETERS_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    int_fields=_INT_FIELDS,
    float_fields=_FLOAT_FIELDS,
    operator_fields=_OPERATOR_FIELDS,
    enum_fields={
        "standard_type": ASSAY_PARAMETER_STANDARD_TYPES,
        "standard_units": ASSAY_PARAMETER_STANDARD_UNITS,
    },
    special_rules=_SPECIAL_RULE_COMPONENTS,
    unit_fields=_RAW_UNIT_FIELDS,
    null_fields=chembl_pseudo_null_fields("assay_parameters"),
)

CHEMBL_ASSAY_PARAMETERS_PROFILE.assert_covers_schema(
    CHEMBL_ASSAY_PARAMETERS_SCHEMA_FIELDS
)
