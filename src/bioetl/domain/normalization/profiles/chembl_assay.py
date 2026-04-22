"""Normalization profile for the ChEMBL Assay Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.identifiers import normalize_ontology_id
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.normalization.rules import normalize_cross_pipeline_case
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.constants import (
    ASSAY_CATEGORIES,
    ASSAY_GROUPS,
    ASSAY_TEST_TYPES,
    ASSAY_TYPES,
    CONFIDENCE_DESCRIPTIONS,
    RELATIONSHIP_TYPES,
    SUBCELLULAR_FRACTIONS,
)

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

# Use enum configurations from centralized constants (loaded from YAML)
# These are already properly loaded and don't require runtime I/O

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
_NULL_FIELDS = chembl_pseudo_null_fields("assay")


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


_SPECIAL_RULE_COMPONENTS = {
    "bao_format": (
        normalize_ontology_id,
        "Normalize BAO ontology ID to underscore format (e.g., 'BAO:0000190' -> 'BAO_0000190').",
    ),
}

# Enum fields for strict validation
_ENUM_FIELDS = {
    "assay_type": ASSAY_TYPES,
    "assay_test_type": ASSAY_TEST_TYPES,
    "assay_category": ASSAY_CATEGORIES,
    "assay_group": ASSAY_GROUPS,
    "confidence_description": CONFIDENCE_DESCRIPTIONS,
    "relationship_type": RELATIONSHIP_TYPES,
}

CHEMBL_ASSAY_PROFILE = build_standard_profile(
    profile_name="chembl.assay",
    description="Canonical field-level normalization policy for the ChEMBL Assay Silver schema.",
    schema_fields=CHEMBL_ASSAY_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
    float_fields=_FLOAT_FIELDS,
    json_string_fields=_JSON_STRING_FIELDS,
    enum_fields=_ENUM_FIELDS,
    special_rules=_SPECIAL_RULE_COMPONENTS,
    null_fields=_NULL_FIELDS,
)

CHEMBL_ASSAY_PROFILE.assert_covers_schema(CHEMBL_ASSAY_SCHEMA_FIELDS)
