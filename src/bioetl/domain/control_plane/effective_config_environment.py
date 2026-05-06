"""Shared execution-environment provenance policy for effective-config artifacts."""

from __future__ import annotations

AMBIENT_ENVIRONMENT_POLICY = "excluded_unless_explicitly_materialized"

SEMANTIC_RUNTIME_ENV_DEPENDENCIES: tuple[str, ...] = (
    "settings.env",
    "settings.debug",
    "settings.test_mode",
    "settings.data_dir",
    "settings.strict_error_handling",
    "settings.strict_medallion",
    "settings.silver_dedup_timeout_seconds",
    "settings.pii_salt_rotation_active",
    "settings.json_encoder",
    "settings.default_email",
    "settings.pii_salt_current",
    "settings.pii_salt_next",
    "settings.pubmed_api_key",
    "settings.uniprot_api_key",
    "settings.openalex_api_key",
    "settings.semanticscholar_api_key",
    "settings.pipeline.batch_size",
    "settings.pipeline.checkpoint_interval",
    "settings.pipeline.relaxed_dq",
    "settings.pipeline.health_check_mode",
    "settings.pipeline.control_plane.required_persistence_profile",
    "settings.pipeline.control_plane.run_manifest_enabled",
    "settings.pipeline.control_plane.run_ledger_enabled",
    "settings.pipeline.control_plane.checkpoint_compatibility_policy",
    "settings.observability.metrics_enabled",
    "settings.observability.tracing_enabled",
    "settings.observability.audit_enabled",
)


def semantic_runtime_env_dependencies() -> tuple[str, ...]:
    """Return the canonical semantic runtime dependency inventory."""
    return SEMANTIC_RUNTIME_ENV_DEPENDENCIES
