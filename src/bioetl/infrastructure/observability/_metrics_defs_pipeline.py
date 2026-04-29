"""Pipeline lifecycle, transform, shutdown, and adaptive-memory metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

__all__ = [
    "CHECKPOINT_COMPATIBILITY_EVENTS_TOTAL",
    "CHECKPOINT_LOAD_EVENTS_TOTAL",
    "CHECKPOINT_OPERATOR_DURATION_SECONDS",
    "CHECKPOINT_OPERATOR_OPERATIONS_TOTAL",
    "CHECKPOINT_SAVE_DURATION_SECONDS",
    "CHECKPOINT_SAVE_EVENTS_TOTAL",
    "COMPOSITE_SOURCE_SELECTION_TOTAL",
    "CONTROL_PLANE_LEDGER_APPENDS_TOTAL",
    "CONTROL_PLANE_LIFECYCLE_APPLY_TOTAL",
    "CONTROL_PLANE_LIFECYCLE_DELETED_TOTAL",
    "CONTROL_PLANE_LIFECYCLE_DELETE_CANDIDATES",
    "CONTROL_PLANE_MANIFEST_WRITES_TOTAL",
    "CONTROL_PLANE_READS_TOTAL",
    "CONTROL_PLANE_READ_DURATION_SECONDS",
    "CONTROL_PLANE_TERMINAL_EVENTS_TOTAL",
    "DQ_CONTEXT_BUILD_FAILURES_TOTAL",
    "DQ_REPORT_GENERATED_TOTAL",
    "DQ_REPORT_SKIPPED_TOTAL",
    "DQ_SOFT_THRESHOLD_EXCEEDED",
    "FILTER_COMBINATIONS_LOADED_TOTAL",
    "LINEAGE_FRAGMENTS_EMITTED_TOTAL",
    "LINEAGE_REFS_MISSING_TOTAL",
    "MEMORY_BATCH_RESIZE_EVENTS_TOTAL",
    "MEMORY_MONITOR_FALLBACK_EVENTS_TOTAL",
    "MEMORY_PRESSURE_EVENTS_TOTAL",
    "MEMORY_PRESSURE_STATE",
    "OBSERVABILITY_EVENTS_TOTAL",
    "PHASE_DURATION_SECONDS",
    "PIPELINE_RUNS_TOTAL",
    "POSTRUN_PHASE_DURATION_SECONDS",
    "POSTRUN_PHASE_EVENTS_TOTAL",
    "REPLAY_RECONSTRUCTABILITY_EVENTS_TOTAL",
    "SHUTDOWN_COMPLETED",
    "SHUTDOWN_INITIATED",
    "STORAGE_OPTIMIZATION_TOTAL",
    "STRUCTURAL_POLICY_EVENTS_TOTAL",
    "STRUCTURAL_POLICY_SHADOW_COMPARISONS_TOTAL",
    "TRACED_RUNS_TOTAL",
    "TRANSFORM_DURATION_SECONDS",
    "TRANSFORM_ERRORS_TOTAL",
]

PIPELINE_RUNS_TOTAL = Counter(
    "bioetl_pipeline_runs_total",
    "Total number of pipeline runs",
    ["pipeline", "run_type", "status"],
)

PHASE_DURATION_SECONDS = Histogram(
    "bioetl_phase_duration_seconds",
    "Duration of pipeline lifecycle phases in seconds",
    ["pipeline", "phase", "status"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
)

POSTRUN_PHASE_EVENTS_TOTAL = Counter(
    "bioetl_postrun_phase_events_total",
    "Total bounded postrun phase outcomes by pipeline, phase, and status",
    ["pipeline", "phase", "status"],
)

POSTRUN_PHASE_DURATION_SECONDS = Histogram(
    "bioetl_postrun_phase_duration_seconds",
    "Duration of postrun subphases in seconds",
    ["pipeline", "phase", "status"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
)

OBSERVABILITY_EVENTS_TOTAL = Counter(
    "bioetl_observability_events_total",
    "Unified observability events emitted by pipeline observer",
    ["event", "provider", "pipeline", "severity", "error_type"],
)

TRANSFORM_DURATION_SECONDS = Histogram(
    "bioetl_transform_duration_seconds",
    "Duration of data transformation in seconds",
    ["provider", "entity_type"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

TRANSFORM_ERRORS_TOTAL = Counter(
    "bioetl_transform_errors_total",
    "Total transformation errors",
    ["provider", "entity_type", "error_type"],
)

STRUCTURAL_POLICY_EVENTS_TOTAL = Counter(
    "bioetl_structural_policy_events_total",
    "Total structural-policy events emitted by transformer structural enforcement",
    ["provider", "entity_type", "action"],
)

STRUCTURAL_POLICY_SHADOW_COMPARISONS_TOTAL = Counter(
    "bioetl_structural_policy_shadow_comparisons_total",
    "Total shadow comparisons between structural policy and semantic silver filters",
    ["provider", "entity_type", "comparison"],
)

DQ_SOFT_THRESHOLD_EXCEEDED = Counter(
    "bioetl_dq_soft_threshold_exceeded",
    "Total times DQ soft threshold was exceeded",
    ["pipeline"],
)

DQ_CONTEXT_BUILD_FAILURES_TOTAL = Counter(
    "bioetl_dq_context_build_failures_total",
    "Total failures while building DQ dataframe context for report generation",
    ["pipeline", "stage", "reason"],
)

DQ_REPORT_SKIPPED_TOTAL = Counter(
    "bioetl_dq_report_skipped_total",
    "Total DQ report generation skips by pipeline and medallion stage",
    ["pipeline", "stage", "reason"],
)

DQ_REPORT_GENERATED_TOTAL = Counter(
    "bioetl_dq_report_generated_total",
    "Total successfully generated DQ reports by pipeline and medallion stage",
    ["pipeline", "stage"],
)

SHUTDOWN_INITIATED = Counter(
    "bioetl_shutdown_initiated",
    "Total shutdown initiations",
    ["reason"],
)

SHUTDOWN_COMPLETED = Counter(
    "bioetl_shutdown_completed",
    "Total shutdown completions",
    ["reason"],
)

STORAGE_OPTIMIZATION_TOTAL = Counter(
    "bioetl_storage_optimization_total",
    "Total storage optimization operations",
    ["pipeline", "status"],
)

FILTER_COMBINATIONS_LOADED_TOTAL = Counter(
    "bioetl_filter_combinations_loaded_total",
    "Total filter combinations loaded from multi-filter source",
    ["pipeline", "source_file"],
)

CONTROL_PLANE_MANIFEST_WRITES_TOTAL = Counter(
    "bioetl_control_plane_manifest_writes_total",
    "Total immutable run-manifest persistence attempts",
    ["pipeline", "run_type", "status"],
)

CONTROL_PLANE_LEDGER_APPENDS_TOTAL = Counter(
    "bioetl_control_plane_ledger_appends_total",
    "Total append attempts for run-ledger entries",
    ["pipeline", "event_type", "status"],
)

CONTROL_PLANE_TERMINAL_EVENTS_TOTAL = Counter(
    "bioetl_control_plane_terminal_events_total",
    "Total terminal run outcomes mirrored from persisted run-ledger entries",
    ["pipeline", "terminal_status"],
)

CONTROL_PLANE_READS_TOTAL = Counter(
    "bioetl_control_plane_reads_total",
    "Total control-plane read and lookup operations by store, operation, and outcome",
    ["store", "operation", "status"],
)

CONTROL_PLANE_READ_DURATION_SECONDS = Histogram(
    "bioetl_control_plane_read_duration_seconds",
    "Latency of control-plane read and lookup operations in seconds",
    ["store", "operation", "status"],
    buckets=[0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

CONTROL_PLANE_LIFECYCLE_DELETED_TOTAL = Counter(
    "bioetl_control_plane_lifecycle_deleted_total",
    "Total control-plane lifecycle artifacts deleted by retention application",
    ["surface"],
)

CONTROL_PLANE_LIFECYCLE_DELETE_CANDIDATES = Gauge(
    "bioetl_control_plane_lifecycle_delete_candidates",
    "Current number of control-plane lifecycle delete candidates in the latest plan",
)

CONTROL_PLANE_LIFECYCLE_APPLY_TOTAL = Counter(
    "bioetl_control_plane_lifecycle_apply_total",
    "Total control-plane lifecycle plan apply attempts by dry-run policy",
    ["dry_run"],
)

TRACED_RUNS_TOTAL = Counter(
    "bioetl_traced_runs_total",
    "Total pipeline runs that started with real tracing enabled",
    ["pipeline", "run_type"],
)

REPLAY_RECONSTRUCTABILITY_EVENTS_TOTAL = Counter(
    "bioetl_replay_reconstructability_events_total",
    "Total replay reconstructability observations recorded during manifest assembly",
    ["pipeline", "replay_capability", "strict_requirement", "status"],
)

MEMORY_PRESSURE_EVENTS_TOTAL = Counter(
    "bioetl_memory_pressure_events_total",
    "Total adaptive-memory decisions that observed active pressure",
    ["pipeline", "stage", "reason", "monitor_mode", "status"],
)

MEMORY_BATCH_RESIZE_EVENTS_TOTAL = Counter(
    "bioetl_memory_batch_resize_events_total",
    "Total adaptive-memory decisions that changed batch size",
    ["pipeline", "stage", "reason", "monitor_mode", "status"],
)

MEMORY_MONITOR_FALLBACK_EVENTS_TOTAL = Counter(
    "bioetl_memory_monitor_fallback_events_total",
    "Total adaptive-memory decisions emitted while using fallback monitor modes",
    ["pipeline", "stage", "reason", "monitor_mode", "status"],
)

MEMORY_PRESSURE_STATE = Gauge(
    "bioetl_memory_pressure_state",
    "Current bounded adaptive-memory pressure state for the latest decision",
    ["pipeline", "stage", "reason", "monitor_mode", "status"],
)

CHECKPOINT_COMPATIBILITY_EVENTS_TOTAL = Counter(
    "bioetl_checkpoint_compatibility_events_total",
    "Total checkpoint compatibility outcomes observed during resume validation",
    ["pipeline", "disposition"],
)

CHECKPOINT_LOAD_EVENTS_TOTAL = Counter(
    "bioetl_checkpoint_load_events_total",
    "Total checkpoint load decisions observed during runtime and composite resume paths",
    ["pipeline", "status"],
)

CHECKPOINT_OPERATOR_OPERATIONS_TOTAL = Counter(
    "bioetl_checkpoint_operator_operations_total",
    "Total checkpoint admin/operator actions by bounded operation and status",
    ["operation", "status"],
)

CHECKPOINT_OPERATOR_DURATION_SECONDS = Histogram(
    "bioetl_checkpoint_operator_duration_seconds",
    "Duration of checkpoint admin/operator actions in seconds",
    ["operation", "status"],
    buckets=[0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

CHECKPOINT_SAVE_EVENTS_TOTAL = Counter(
    "bioetl_checkpoint_save_events_total",
    "Total checkpoint save outcomes observed during runtime and composite persistence paths",
    ["pipeline", "operation", "status"],
)

CHECKPOINT_SAVE_DURATION_SECONDS = Histogram(
    "bioetl_checkpoint_save_duration_seconds",
    "Duration of checkpoint save operations in seconds",
    ["pipeline", "operation", "status"],
    buckets=[0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

LINEAGE_FRAGMENTS_EMITTED_TOTAL = Counter(
    "bioetl_lineage_fragments_emitted_total",
    "Total lineage fragment persistence attempts by pipeline and layer",
    ["pipeline", "layer", "status"],
)

LINEAGE_REFS_MISSING_TOTAL = Counter(
    "bioetl_lineage_refs_missing_total",
    "Total writes that detected missing upstream lineage references",
    ["pipeline", "layer", "ref_type"],
)

COMPOSITE_SOURCE_SELECTION_TOTAL = Counter(
    "bioetl_composite_source_selection_total",
    "Total low-cardinality composite source-selection decisions recorded at persistence time",
    ["pipeline", "decision_type", "selected_source"],
)
