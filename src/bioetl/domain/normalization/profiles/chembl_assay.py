"""Normalization profile for the ChEMBL Assay Silver schema."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.domain.normalization.chembl import BAO_ONTOLOGY_VERSION
from bioetl.domain.normalization.profiles._profile_ontology_companion_normalizers import (
    build_obo_companion_iri_normalizer,
    build_obo_companion_mapping_status_normalizer,
    build_obo_companion_version_normalizer,
)
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_bao_identifier,
    normalize_profile_chembl_organism_name,
    normalize_profile_governed_vocabulary,
    normalize_profile_text,
)
from bioetl.domain.normalization.rules import normalize_cross_pipeline_case
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.constants import ONTOLOGY_MAPPING_STATUSES

from ._chembl_bao_label_normalizers import (
    normalize_profile_bao_label_from_bao_format as normalize_bao_label_from_bao_format,
)
from ._chembl_policy_registry import (
    chembl_controlled_family_fields,
    chembl_ontology_family_fields,
)
from ._chembl_reference_identifier_rules import chembl_reference_identifier_rules
from ._chembl_vocab import chembl_enum
from .chembl_json_ordering_policy import chembl_json_fields

__all__ = [
    "ASSAY_CATEGORIES",
    "ASSAY_GROUPS",
    "ASSAY_TEST_TYPES",
    "ASSAY_TYPES",
    "CHEMBL_ASSAY_PROFILE",
    "CHEMBL_ASSAY_SCHEMA_FIELDS",
    "CONFIDENCE_DESCRIPTIONS",
    "RELATIONSHIP_TYPES",
    "SUBCELLULAR_FRACTIONS",
    "create_case_normalizer",
]

ASSAY_CATEGORIES = chembl_enum("assay", "assay_category")
ASSAY_GROUPS = chembl_enum("assay", "assay_group")
ASSAY_TEST_TYPES = chembl_enum("assay", "assay_test_type")
ASSAY_TYPES = chembl_enum("assay", "assay_type")
CONFIDENCE_DESCRIPTIONS = chembl_enum("assay", "confidence_description")
RELATIONSHIP_TYPES = chembl_enum("assay", "relationship_type")
SUBCELLULAR_FRACTIONS = chembl_enum("assay", "subcellular_fraction")

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
_INT_FIELDS = frozenset(
    {"assay_taxonomy_id", "confidence_score", "src_id", "variant_taxonomy_id"}
)
_FLOAT_FIELDS = frozenset({"score"})
_STRICT_JSON_FIELDS = chembl_json_fields("chembl_assay")
_NULL_FIELDS = chembl_pseudo_null_fields("assay")
_BAO_FIELDS = chembl_ontology_family_fields("bao", entity="assay")
_CONTROLLED_FRACTION_FIELDS = chembl_controlled_family_fields(
    "subcellular_fractions",
    entity="assay",
)
_CONTROLLED_CATEGORY_FIELDS = chembl_controlled_family_fields(
    "assay_categories",
    entity="assay",
)
_CONTROLLED_CONFIDENCE_FIELDS = chembl_controlled_family_fields(
    "assay_confidence_descriptions",
    entity="assay",
)
_REFERENCE_IDENTIFIER_RULES = chembl_reference_identifier_rules("assay")

def create_case_normalizer(strategy: str = "uppercase") -> Callable[[str], str | None]:
    """Create a case normalizer function with the specified strategy.

    Args:
        strategy: Case strategy to apply ("uppercase", "lowercase", or "preserve")

    Returns:
        A function that normalizes case according to the specified strategy
    """

    def normalizer(value: str) -> str | None:
        return normalize_cross_pipeline_case(value, strategy)

    return normalizer


# Strict assay enums canonicalize case-insensitively to the registry-defined
# representation and fail closed on unknown values.
_ENUM_FIELDS = {
    "assay_type": ASSAY_TYPES,
    "assay_test_type": ASSAY_TEST_TYPES,
    "assay_group": ASSAY_GROUPS,
    "relationship_type": RELATIONSHIP_TYPES,
    "bao_format_mapping_status": ONTOLOGY_MAPPING_STATUSES,
}
_SPECIAL_RULE_COMPONENTS = {
    **_REFERENCE_IDENTIFIER_RULES,
    "assay_organism": (
        normalize_profile_chembl_organism_name,
        "Normalize ChEMBL assay organism display name using curated organism aliases.",
    ),
    "bao_label": (
        normalize_bao_label_from_bao_format,
        "Normalize BAO label text inside the profile-visible assay contract, "
        "resolving canonical labels from sibling bao_format identifiers when present.",
    ),
    "bao_format_iri": (
        build_obo_companion_iri_normalizer(
            source_field="bao_format",
            canonical_prefix="BAO_",
            ontology_version=BAO_ONTOLOGY_VERSION,
        ),
        "Resolve the BAO format ontology companion bundle from sibling "
        "normalized identifiers and emit the canonical OBO IRI.",
    ),
    "bao_format_mapping_status": (
        build_obo_companion_mapping_status_normalizer(
            source_field="bao_format",
            canonical_prefix="BAO_",
            ontology_version=BAO_ONTOLOGY_VERSION,
        ),
        "Resolve the BAO format ontology companion bundle from sibling "
        "normalized identifiers and emit the canonical mapping-status enum.",
    ),
    "bao_ontology_version": (
        build_obo_companion_version_normalizer(
            source_field="bao_format",
            canonical_prefix="BAO_",
            ontology_version=BAO_ONTOLOGY_VERSION,
        ),
        "Resolve the BAO ontology companion bundle from sibling normalized "
        "identifiers and emit the ontology version when a BAO mapping context exists.",
    ),
    "assay_subcellular_fraction_raw": (
        normalize_profile_text,
        "Preserve the raw assay_subcellular_fraction provider lexeme as trimmed "
        "text before canonical controlled-vocabulary normalization.",
    ),
    **dict.fromkeys(
        sorted(_CONTROLLED_FRACTION_FIELDS),
        (
            lambda value: normalize_profile_governed_vocabulary(
                value,
                allowed_values=SUBCELLULAR_FRACTIONS,
                preserve_unknown=True,
            ),
            "Normalize assay_subcellular_fraction against the shared ChEMBL "
            "subcellular-fraction vocabulary while preserving unknown observed "
            "lexemes for review; the provider-native lexeme is retained "
            "separately in assay_subcellular_fraction_raw.",
        ),
    ),
    **dict.fromkeys(
        sorted(_CONTROLLED_CATEGORY_FIELDS),
        (
            lambda value: normalize_profile_governed_vocabulary(
                value,
                allowed_values=ASSAY_CATEGORIES,
                preserve_unknown=False,
            ),
            "Normalize assay_category against the governed ChEMBL controlled "
            "vocabulary registry, preserving canonical allowed-value casing, "
            "and fail closed on unknown values.",
        ),
    ),
    **dict.fromkeys(
        sorted(_CONTROLLED_CONFIDENCE_FIELDS),
        (
            lambda value: normalize_profile_governed_vocabulary(
                value,
                allowed_values=CONFIDENCE_DESCRIPTIONS,
                preserve_unknown=False,
            ),
            "Normalize confidence_description against the governed ChEMBL "
            "controlled vocabulary registry, preserving canonical allowed-value "
            "casing and failing closed on unknown values to stay aligned with DQ "
            "enum governance.",
        ),
    ),
    **{
        field_name: (
            normalize_profile_bao_identifier,
            f"Normalize BAO {field_name.removeprefix('bao_')} identifier to canonical BAO underscore form.",
        )
        for field_name in sorted(_BAO_FIELDS)
    },
}

CHEMBL_ASSAY_PROFILE = build_standard_profile(
    profile_name="chembl.assay",
    description="Canonical field-level normalization policy for the ChEMBL Assay Silver schema.",
    schema_fields=CHEMBL_ASSAY_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
    float_fields=_FLOAT_FIELDS,
    strict_json_fields=_STRICT_JSON_FIELDS,
    enum_fields=_ENUM_FIELDS,
    special_rules=_SPECIAL_RULE_COMPONENTS,
    null_fields=_NULL_FIELDS,
)

CHEMBL_ASSAY_PROFILE.assert_covers_schema(CHEMBL_ASSAY_SCHEMA_FIELDS)
