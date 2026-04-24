"""Normalization profile for the ChEMBL Assay Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.chembl import normalize_bao_label
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
)
from bioetl.domain.normalization.rules import normalize_cross_pipeline_case
from bioetl.domain.schemas.chembl.assay import AssaySchema

from ._chembl_policy_registry import chembl_ontology_family_fields
from ._chembl_vocab import chembl_enum

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
_INT_FIELDS = frozenset({"confidence_score", "src_id"})
_FLOAT_FIELDS = frozenset({"assay_taxonomy_id", "score", "variant_taxonomy_id"})
_STRICT_JSON_FIELDS = frozenset(
    {
        "assay_classifications",
        "assay_parameters",
        "variant_sequence_json",
    }
)
_NULL_FIELDS = chembl_pseudo_null_fields("assay")
_BAO_FIELDS = chembl_ontology_family_fields("bao", entity="assay")


def _normalize_bao_label_with_profile_context(
    value: object,
    record: dict[str, object] | None = None,
) -> str | None:
    bao_identifier = (
        None
        if record is None
        else normalize_profile_bao_identifier(record.get("bao_format"))
    )
    return normalize_bao_label(value, bao_identifier=bao_identifier)


def create_case_normalizer(strategy: str = "uppercase"):
    """Create a case normalizer function with the specified strategy.

    Args:
        strategy: Case strategy to apply ("uppercase", "lowercase", or "preserve")

    Returns:
        A function that normalizes case according to the specified strategy
    """

    def normalizer(value: str) -> str | None:
        return normalize_cross_pipeline_case(value, strategy)

    return normalizer


# Enum fields for strict validation
_ENUM_FIELDS = {
    "assay_type": ASSAY_TYPES,
    "assay_test_type": ASSAY_TEST_TYPES,
    "assay_category": ASSAY_CATEGORIES,
    "assay_group": ASSAY_GROUPS,
    "confidence_description": CONFIDENCE_DESCRIPTIONS,
    "relationship_type": RELATIONSHIP_TYPES,
}
_SPECIAL_RULE_COMPONENTS = {
    "assay_organism": (
        normalize_profile_chembl_organism_name,
        "Normalize ChEMBL assay organism display name using curated organism aliases.",
    ),
    "bao_label": (
        _normalize_bao_label_with_profile_context,
        "Normalize BAO label text inside the profile-visible assay contract, "
        "resolving canonical labels from sibling bao_format identifiers when present.",
    ),
    "assay_subcellular_fraction": (
        lambda value: normalize_profile_governed_vocabulary(
            value,
            allowed_values=SUBCELLULAR_FRACTIONS,
            preserve_unknown=True,
        ),
        "Normalize assay_subcellular_fraction against the shared ChEMBL subcellular-fraction vocabulary while preserving unknown observed lexemes for review.",
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
