"""Normalization profile for the ChEMBL Assay Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.rules import normalize_cross_pipeline_case
from bioetl.domain.normalization.identifiers import normalize_ontology_id
from bioetl.domain.config.enum_loader import get_chembl_enum_set
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.schemas.chembl.assay import AssaySchema

__all__ = [
    "ASSAY_TYPES",
    "RELATIONSHIP_TYPES",
    "ASSAY_CATEGORIES",
    "ASSAY_TEST_TYPES",
    "ASSAY_GROUPS",
    "SUBCELLULAR_FRACTIONS",
    "CONFIDENCE_DESCRIPTIONS",
    "CHEMBL_ASSAY_PROFILE",
    "CHEMBL_ASSAY_SCHEMA_FIELDS",
    "create_case_normalizer",
]

# Load enum configurations from external YAML file
ASSAY_TYPES = get_chembl_enum_set("assay", "types")
RELATIONSHIP_TYPES = get_chembl_enum_set("assay", "relationship_types")
ASSAY_CATEGORIES = get_chembl_enum_set("assay", "categories")
ASSAY_TEST_TYPES = get_chembl_enum_set("assay", "test_types")
ASSAY_GROUPS = get_chembl_enum_set("assay", "assay_groups")
SUBCELLULAR_FRACTIONS = get_chembl_enum_set("assay", "subcellular_fractions")
CONFIDENCE_DESCRIPTIONS = get_chembl_enum_set("assay", "confidence_descriptions")

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


# Special rules for enum fields that need case normalization
_SPECIAL_RULE_COMPONENTS = {
    "assay_type": (
        create_case_normalizer("uppercase"),
        "Normalize assay_type to uppercase enum value.",
    ),
    "assay_test_type": (
        create_case_normalizer("preserve"),
        "Normalize assay_test_type preserving original case (e.g., 'In vivo').",
    ),
    "assay_category": (
        create_case_normalizer("preserve"),
        "Normalize assay_category preserving original case.",
    ),
    "relationship_type": (
        create_case_normalizer("uppercase"),
        "Normalize relationship_type to uppercase enum value.",
    ),
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
    special_rules=_SPECIAL_RULE_COMPONENTS,
)

CHEMBL_ASSAY_PROFILE.assert_covers_schema(CHEMBL_ASSAY_SCHEMA_FIELDS)
