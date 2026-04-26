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
    "openalex": ["mailto"],
    "crossref": ["mailto"],
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
        "filter_batch_size",
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

TRANSITIONAL_PIPELINE_KEYS: Final[frozenset[str]] = frozenset({"filter_batch_size"})

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
    }
)

FILTER_ALLOWED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "version",
        "provider",
        "entity",
        "input_filter",
        "silver_filters",
        "gold_filters",
        "extraction_params",
        "batch_size",
        "page_size",
    }
)

CONTRACT_ALLOWED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "primary_key",
        "merge_keys",
        "rename_map",
        "hash_include",
        "hash_exclude",
    }
)

REQUIRED_ENTITY_SECTIONS: Final[frozenset[str]] = frozenset(
    {"pipeline", "schema", "quality", "filters", "contracts"}
)

__all__ = [
    "COMPOSITE_ALLOWED_KEYS",
    "CONTRACT_ALLOWED_KEYS",
    "ENTITY_ALLOWED_KEYS",
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
