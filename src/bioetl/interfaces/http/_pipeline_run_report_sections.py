"""Stable field ordering for Run Explorer report sections."""

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
