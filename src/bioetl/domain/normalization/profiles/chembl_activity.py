"""Normalization profile for the ChEMBL Activity Silver schema."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.domain.normalization.rules import normalize_cross_pipeline_case
from bioetl.domain.schemas.constants import ONTOLOGY_MAPPING_STATUSES

from ._chembl_activity_fields import (
    ACTIVITY_ACTION_TYPES,
    ACTIVITY_STANDARD_TYPES,
    ACTIVITY_STANDARD_UNITS,
    ASSAY_TYPES,
    CHEMBL_ACTIVITY_SCHEMA_FIELDS,
    DATA_VALIDITY_COMMENTS,
    FLOAT_FIELDS,
    INT_FIELDS,
    META_FIELDS,
    SET_LIKE_FIELDS,
    STANDARD_RELATIONS,
)
from ._chembl_bao_label_normalizers import normalize_profile_bao_label_from_bao_format
from ._chembl_policy_registry import (
    chembl_controlled_family_fields,
    chembl_flag_family_fields,
    chembl_ontology_family_fields,
)
from ._chembl_reference_identifier_rules import chembl_reference_identifier_rules
from ._standard_profile_builder import build_standard_profile
from .chembl_pseudo_nulls import chembl_pseudo_null_fields
from .profile_normalizers import (
    normalize_profile_activity_bao_endpoint_iri,
    normalize_profile_activity_bao_endpoint_mapping_status,
    normalize_profile_activity_bao_format_iri,
    normalize_profile_activity_bao_format_mapping_status,
    normalize_profile_activity_bao_ontology_version,
    normalize_profile_activity_qudt_ontology_version,
    normalize_profile_activity_qudt_unit_iri,
    normalize_profile_activity_qudt_unit_mapping_status,
    normalize_profile_activity_uo_ontology_version,
    normalize_profile_activity_uo_unit_iri,
    normalize_profile_activity_uo_unit_mapping_status,
    normalize_profile_bao_identifier,
    normalize_profile_canonical_smiles,
    normalize_profile_chembl_organism_name,
    normalize_profile_enum,
    normalize_profile_governed_uppercase_vocabulary,
    normalize_profile_operator,
    normalize_profile_qudt_unit_reference,
    normalize_profile_standard_unit_enum,
)

__all__ = [
    "ACTIVITY_STANDARD_TYPES",
    "ACTIVITY_STANDARD_UNITS",
    "ASSAY_TYPES",
    "CHEMBL_ACTIVITY_PROFILE",
    "CHEMBL_ACTIVITY_SCHEMA_FIELDS",
    "DATA_VALIDITY_COMMENTS",
    "NULL_FIELDS",
    "STANDARD_RELATIONS",
]


def create_case_normalizer(strategy: str = "uppercase") -> Callable[[str], str | None]:
    """Create a case normalizer function for profile use.

    Args:
        strategy: Case strategy ("uppercase", "lowercase", or "preserve")

    Returns:
        Normalizer function suitable for profile special_rules
    """

    def normalizer(value: str) -> str | None:
        return normalize_cross_pipeline_case(value, strategy)

    return normalizer


# Enum fields for strict validation
_ENUM_FIELDS = {
    "standard_relation": STANDARD_RELATIONS,
    "standard_type": ACTIVITY_STANDARD_TYPES,
    "assay_type": ASSAY_TYPES,
}
_ONTOLOGY_ID_FIELDS = chembl_ontology_family_fields("uo", entity="activity")
_CONTROLLED_ACTION_TYPE_FIELDS = chembl_controlled_family_fields(
    "activity_action_types",
    entity="activity",
)
_RAW_UNIT_FIELDS = chembl_controlled_family_fields("raw_units", entity="activity")
_BAO_FIELDS = chembl_ontology_family_fields("bao", entity="activity")
_STRICT_JSON_FIELDS = SET_LIKE_FIELDS
_REFERENCE_IDENTIFIER_RULES = chembl_reference_identifier_rules("activity")


def normalize_activity_standard_units(value: object) -> object:
    """Normalize one activity standard-unit field against the strict enum."""
    return normalize_profile_standard_unit_enum(
        value,
        allowed_values=ACTIVITY_STANDARD_UNITS,
    )


def normalize_activity_action_type(value: object) -> object:
    """Normalize one activity action-type label against the governed registry."""
    return normalize_profile_governed_uppercase_vocabulary(
        value,
        allowed_values=ACTIVITY_ACTION_TYPES,
        preserve_unknown=True,
    )


_SPECIAL_RULE_COMPONENTS = {
    **_REFERENCE_IDENTIFIER_RULES,
    "canonical_smiles": (
        normalize_profile_canonical_smiles,
        "Normalize canonical SMILES via the domain SMILES Value Object; invalid values collapse to None.",
    ),
    "bao_label": (
        normalize_profile_bao_label_from_bao_format,
        "Normalize BAO label text inside the profile-visible activity contract, "
        "resolving canonical labels from sibling bao_format identifiers when present.",
    ),
    **dict.fromkeys(
        sorted(_CONTROLLED_ACTION_TYPE_FIELDS),
        (
            normalize_activity_action_type,
            "Normalize action_type against the observed ChEMBL activity-action "
            "vocabulary while preserving unknown uppercase lexemes for review; "
            "the field remains governed as allowed-or-unknown rather than a "
            "fail-closed closed-set validator.",
        ),
    ),
    "standard_relation": (
        lambda value: normalize_profile_operator(
            value,
            allowed_values=STANDARD_RELATIONS,
        ),
        "Normalize standard_relation to a canonical ASCII operator enum.",
    ),
    "assay_type": (
        lambda value: normalize_profile_enum(value, allowed_values=ASSAY_TYPES),
        "Normalize assay_type to uppercase enum value and collapse unknown values to None.",
    ),
    "standard_units": (
        normalize_activity_standard_units,
        "Normalize standard_units against the published ChEMBL "
        "standard-unit enum after canonical unit alias collapse; "
        "unknown values collapse to None.",
    ),
    "qudt_units": (
        normalize_profile_qudt_unit_reference,
        "Normalize QUDT unit reference tokens and URIs while "
        "preserving unknown unit lexemes for ontology review and "
        "companion mapping-status resolution.",
    ),
    "target_organism": (
        normalize_profile_chembl_organism_name,
        "Normalize target organism display name using the shared curated ChEMBL organism aliases.",
    ),
    **{
        field_name: (
            normalize_profile_bao_identifier,
            f"Normalize BAO {field_name.removeprefix('bao_')} identifier to canonical BAO underscore form.",
        )
        for field_name in sorted(_BAO_FIELDS)
    },
    "bao_endpoint_iri": (
        normalize_profile_activity_bao_endpoint_iri,
        "Resolve the BAO endpoint ontology companion bundle from sibling "
        "normalized identifiers and emit the canonical OBO IRI.",
    ),
    "bao_endpoint_mapping_status": (
        normalize_profile_activity_bao_endpoint_mapping_status,
        "Resolve the BAO endpoint ontology companion bundle from sibling "
        "normalized identifiers and emit the canonical mapping-status enum.",
    ),
    "bao_format_iri": (
        normalize_profile_activity_bao_format_iri,
        "Resolve the BAO format ontology companion bundle from sibling "
        "normalized identifiers and emit the canonical OBO IRI.",
    ),
    "bao_format_mapping_status": (
        normalize_profile_activity_bao_format_mapping_status,
        "Resolve the BAO format ontology companion bundle from sibling "
        "normalized identifiers and emit the canonical mapping-status enum.",
    ),
    "bao_ontology_version": (
        normalize_profile_activity_bao_ontology_version,
        "Resolve the BAO ontology companion bundle from sibling normalized "
        "identifiers and emit the shared ontology version when a BAO "
        "mapping context exists.",
    ),
    "uo_unit_iri": (
        normalize_profile_activity_uo_unit_iri,
        "Resolve the Units Ontology companion bundle from sibling normalized "
        "identifiers and emit the canonical OBO IRI.",
    ),
    "uo_unit_mapping_status": (
        normalize_profile_activity_uo_unit_mapping_status,
        "Resolve the Units Ontology companion bundle from sibling normalized "
        "identifiers and emit the canonical mapping-status enum.",
    ),
    "uo_ontology_version": (
        normalize_profile_activity_uo_ontology_version,
        "Resolve the Units Ontology companion bundle from sibling normalized "
        "identifiers and emit the ontology version.",
    ),
    "qudt_unit_iri": (
        normalize_profile_activity_qudt_unit_iri,
        "Resolve the QUDT companion bundle from sibling normalized unit "
        "tokens and emit the canonical QUDT unit IRI.",
    ),
    "qudt_unit_mapping_status": (
        normalize_profile_activity_qudt_unit_mapping_status,
        "Resolve the QUDT companion bundle from sibling normalized unit "
        "tokens and emit the canonical mapping-status enum.",
    ),
    "qudt_ontology_version": (
        normalize_profile_activity_qudt_ontology_version,
        "Resolve the QUDT companion bundle from sibling normalized unit "
        "tokens and emit the ontology version.",
    ),
}


NULL_FIELDS = chembl_pseudo_null_fields("activity")

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
    flag_fields=chembl_flag_family_fields("binary_flags", entity="activity"),
    operator_fields=chembl_controlled_family_fields("operators", entity="activity"),
    set_like_fields=SET_LIKE_FIELDS,
    strict_json_fields=_STRICT_JSON_FIELDS,
    ontology_id_fields=_ONTOLOGY_ID_FIELDS,
    enum_fields={
        "standard_relation": STANDARD_RELATIONS,
        "standard_type": ACTIVITY_STANDARD_TYPES,
        "standard_units": ACTIVITY_STANDARD_UNITS,
        "assay_type": ASSAY_TYPES,
        "data_validity_comment": DATA_VALIDITY_COMMENTS,
        "bao_endpoint_mapping_status": ONTOLOGY_MAPPING_STATUSES,
        "bao_format_mapping_status": ONTOLOGY_MAPPING_STATUSES,
        "uo_unit_mapping_status": ONTOLOGY_MAPPING_STATUSES,
        "qudt_unit_mapping_status": ONTOLOGY_MAPPING_STATUSES,
    },
    special_rules=_SPECIAL_RULE_COMPONENTS,
    unit_fields=_RAW_UNIT_FIELDS,
    null_fields=NULL_FIELDS,
)

CHEMBL_ACTIVITY_PROFILE.assert_covers_schema(CHEMBL_ACTIVITY_SCHEMA_FIELDS)
