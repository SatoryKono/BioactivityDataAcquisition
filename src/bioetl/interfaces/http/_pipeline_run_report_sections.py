"""Stable field ordering for Run Explorer report sections."""

from __future__ import annotations

# Canonical reconciliation key order for Run Explorer panel 3015 (REC-04).
_RECONCILIATION_ROW_ORDER: tuple[str, ...] = (
    "silver_accounted",
    "silver_delta",
    "silver_vs_bronze_status",
    "gold_accounted",
    "gold_delta",
    "gold_vs_silver_status",
)

# pipeline_run_report_v1.layers required keys (D6-IA-02).
_LAYER_ROW_ORDER: tuple[str, ...] = (
    "bronze_records",
    "silver_valid",
    "silver_filtered_out",
    "silver_quarantined",
    "silver_skipped",
    "silver_deduplicated",
    "gold_written",
    "gold_excluded_by_contract",
    "gold_quarantined",
    "gold_skipped",
    "gold_deduplicated",
)

# Optional failure object keys (D6-IA-01).
_FAILURE_ROW_ORDER: tuple[str, ...] = (
    "error_type",
    "error_message",
    "failed_stage",
    "exit_hint",
)

# Report identity keys surfaced on Run Explorer 3022 (D6-IA-09).
_IDENTITY_ROW_ORDER: tuple[str, ...] = (
    "run_id",
    "pipeline_name",
    "run_type",
    "status",
    "started_at",
    "completed_at",
    "duration_seconds",
    "tracking_coverage",
    "workflow_id",
    "workflow_run_id",
    "workflow_step_id",
    "manifest_id",
    "provider",
    "entity",
)

# Grafana selector sentinels for "no concrete run selected" (never a real run_id).
_UNRESOLVED_RUN_ID_SENTINELS = frozenset(
    {
        "",
        "-",
        "all",
        "All",
        "$__all",
        "unknown",
        "None",
        "null",
    }
)

_REASON_OPERATOR_LABELS: dict[str, str] = {
    "gold_contract_schema_failure": "Excluded by Gold schema contract",
    "gold_contract_required_failure": "Excluded by Gold required-field contract",
    "gold_contract_reference_failure": "Excluded by Gold reference contract",
    "gold_semantic_business_exclusion": "Excluded by Gold business rule",
    "gold_semantic_profile_exclusion": "Excluded by Gold profile rule",
    "SCHEMA_VALIDATION_FAILURE": "Silver schema validation failed",
    "DQ_THRESHOLD_VIOLATION": "DQ threshold exceeded",
    "structural_policy_required_missing": "Required Silver field missing",
    "structural_policy_null_optional_forbidden": "Forbidden null in optional Silver field",
    "structural_policy_type_mismatch": "Silver type mismatch",
    "FILTERED_OUT_SILVER": "Filtered out in Silver",
    "DEDUP_KEY_COLLISION": "Deduplicated on business key",
}

_ARTIFACT_TITLES: dict[str, str] = {
    "pipeline_run_report_json": "Report JSON",
    "pipeline_run_report_md": "Readable Markdown report",
}

_ARTIFACT_ACTIONS: dict[str, str] = {
    "pipeline_run_report_json": "Download",
    "pipeline_run_report_md": "Open",
}


def _is_unresolved_run_scope(run_id: str) -> bool:
    """Return True when run_id is a dashboard no-selection sentinel."""
    token = run_id.strip()
    return token in _UNRESOLVED_RUN_ID_SENTINELS
