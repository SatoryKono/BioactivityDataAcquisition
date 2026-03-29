"""Pipeline lifecycle, transform, and shutdown metrics."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

__all__ = [
    "CHECKPOINT_COMPATIBILITY_EVENTS_TOTAL",
    "COMPOSITE_SOURCE_SELECTION_TOTAL",
    "CONTROL_PLANE_READ_DURATION_SECONDS",
    "CONTROL_PLANE_READS_TOTAL",
    "CONTROL_PLANE_LEDGER_APPENDS_TOTAL",
    "CONTROL_PLANE_MANIFEST_WRITES_TOTAL",
    "DQ_CONTEXT_BUILD_FAILURES_TOTAL",
    "DQ_REPORT_GENERATED_TOTAL",
    "DQ_REPORT_SKIPPED_TOTAL",
    "DQ_SOFT_THRESHOLD_EXCEEDED",
    "FILTER_COMBINATIONS_LOADED_TOTAL",
    "LINEAGE_FRAGMENTS_EMITTED_TOTAL",
    "LINEAGE_REFS_MISSING_TOTAL",
    "OBSERVABILITY_EVENTS_TOTAL",
    "PHASE_DURATION_SECONDS",
    "PIPELINE_RUNS_TOTAL",
    "SHUTDOWN_COMPLETED",
    "SHUTDOWN_INITIATED",
    "STORAGE_OPTIMIZATION_TOTAL",
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

CHECKPOINT_COMPATIBILITY_EVENTS_TOTAL = Counter(
    "bioetl_checkpoint_compatibility_events_total",
    "Total checkpoint compatibility outcomes observed during resume validation",
    ["pipeline", "disposition"],
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
