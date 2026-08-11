"""Shared config CI contract for scripts, tests, and docs.

This module is the single normative source for config-governance constants used
by pre-commit checks, architecture tests, and documentation references.

Status semantics:
- active: accepted by current CI/runtime-facing config governance
- retired: no longer part of the active contract and must be rejected
- transitional: still accepted for compatibility, but explicitly deprecated
"""

from __future__ import annotations

from typing import Final

LEGACY_ENTITY_NAMES: Final[frozenset[str]] = frozenset(
    {"document", "document_similarity", "document_term"}
)

LEGACY_PATH_FRAGMENTS: Final[tuple[tuple[str, str], ...]] = (
    (f"../../{'dq'}/", "../../quality/"),
    (f"../../{'filter'}/", "../../filters/"),
)

PROVIDER_AUTH_REQUIREMENTS: Final[dict[str, list[str]]] = {
    "openalex": ["api_key_env"],
    "pubmed": ["api_key_env", "email_env"],
}

VALID_LOADING_STRATEGIES: Final[frozenset[str]] = frozenset({"full_scan_only"})

PIPELINE_ALLOWED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "pipeline_name",
        "provider",
        "entity_type",
        "version",
        "description",
        "batch_size",
        "checkpoint_interval",
        "business_primary_keys",
        "field_policy",
        "technical_primary_key",
        "silver_table",
        "gold_table",
        "loading_strategy",
        "source",
        "sink",
        "dq_config_file",
        "dq_overrides",
        "circuit_breaker",
        "filter_config_file",
        "filter_rules",
        "column_groups",
        "input_filter",
        "silver_filters",
        "gold_filters",
        "maintenance",
        "transform",
        "extraction_params",
        "source_profile",
        "page_size_override",
    }
)

RETIRED_PIPELINE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_file",
        "data_schema_file",
        "column_groups_file",
        "source_file",
    }
)

TRANSITIONAL_PIPELINE_KEYS: Final[frozenset[str]] = frozenset()

ENTITY_ALLOWED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "version",
        "provider",
        "entity",
        "pipeline",
        "schema",
        "quality",
        "filters",
        "contracts",
        "hash_policy",
        "source_entities",
        "composite_fields",
        "loading",
        "field_resolution",
        "dq_rules",
        "status",
    }
)

COMPOSITE_ALLOWED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "composite",
        "gold_filters",
        "silver_filters",
        "filter_config_file",
        "filter_rules",
        "maintenance",
    }
)

PROVIDER_ALLOWED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "version",
        "provider",
        "source",
        "quality",
        "filters",
        "entities",
        "entity_notes",
    }
)

QUALITY_ALLOWED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "version",
        "provider",
        "entity",
        "metadata",
        "thresholds",
        "strict_validation",
        "invalid_record_policy",
        "report",
        "common_field_validations",
        "provider_field_validations",
        "entity_field_validations",
        "common_cross_field_validations",
        "entity_cross_field_validations",
        "key_nullability",
        "entity_conditional_validations",
        "provider_conditional_validations",
        "dq_rules",
    }
)

FILTER_ALLOWED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "version",
        "provider",
        "entity",
        "metadata",
        "input_filter",
        "silver_filters",
        "gold_filters",
        "extraction_params",
        "source_profile",
        "batch_size",
        "page_size",
        "filter_rules",
    }
)

CONTRACT_ALLOWED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "primary_key",
        "merge_keys",
        "rename_map",
        "hash_include",
        "hash_exclude",
        "hash_datetime_policy",
        "contract_ref",
        "active_version",
        "rollout",
        "scd_type",
        "gold_business_rules",
    }
)

REQUIRED_ENTITY_SECTIONS: Final[frozenset[str]] = frozenset(
    {"pipeline", "schema", "quality", "filters", "contracts"}
)

# Entity-specific server-side extraction params (ADR-028 §3).
# Keys copied across configs by auto burn-down break VCR replay for unrelated pipelines.
EXTRACTION_PARAM_ALLOWLIST: Final[dict[str, frozenset[str]]] = {
    "chembl/activity": frozenset(
        {
            "assay_type__in",
            "data_validity_comment__isnull",
            "pchembl_value__isnull",
            "potential_duplicate",
            "standard_flag",
            "standard_relation",
            "standard_type__in",
            "standard_units",
            "target_tax_id__isnull",
        }
    ),
    "chembl/assay": frozenset(
        {
            "assay_type__in",
            "confidence_score__gte",
            "relationship_type",
            "target_chembl_id__isnull",
        }
    ),
    "chembl/molecule": frozenset({"inorganic_flag", "molecule_type", "structure_type"}),
    "chembl/target": frozenset({"organism__isnull", "target_type", "tax_id__isnull"}),
    "chembl/publication": frozenset({"doc_type", "year__gte", "year__lte"}),
    "chembl/publication_term": frozenset({"doc_type", "year__gte", "year__lte"}),
}

__all__ = [
    "COMPOSITE_ALLOWED_KEYS",
    "CONTRACT_ALLOWED_KEYS",
    "ENTITY_ALLOWED_KEYS",
    "EXTRACTION_PARAM_ALLOWLIST",
    "FILTER_ALLOWED_KEYS",
    "LEGACY_ENTITY_NAMES",
    "LEGACY_PATH_FRAGMENTS",
    "PIPELINE_ALLOWED_KEYS",
    "PROVIDER_ALLOWED_KEYS",
    "PROVIDER_AUTH_REQUIREMENTS",
    "QUALITY_ALLOWED_KEYS",
    "REQUIRED_ENTITY_SECTIONS",
    "RETIRED_PIPELINE_KEYS",
    "TRANSITIONAL_PIPELINE_KEYS",
    "VALID_LOADING_STRATEGIES",
]
