"""Grouped Prometheus metric registries and machine-readable inventory."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from prometheus_client.metrics import Counter, Gauge, Histogram

from . import metrics_definitions as _metrics
from ._metrics_defs_pipeline_workflow import (
    WORKFLOW_EXPECTED,
    WORKFLOW_PIPELINE_EXPECTED,
)

type PrometheusCounter = Counter
type PrometheusGauge = Gauge
type PrometheusHistogram = Histogram


@dataclass(frozen=True, slots=True)
class MetricRegistryFamily:
    """Logical family of public Prometheus metric registries."""

    family: str
    counters: Mapping[str, PrometheusCounter]
    gauges: Mapping[str, PrometheusGauge]
    histograms: Mapping[str, PrometheusHistogram]


PIPELINE_RUNTIME_REGISTRY = MetricRegistryFamily(
    family="pipeline_runtime",
    counters={
        "bioetl_records_processed_total": _metrics.RECORDS_PROCESSED_TOTAL,
        "bioetl_record_flow_records_total": _metrics.RECORD_FLOW_RECORDS_TOTAL,
        "bioetl_record_flow_invariants_total": _metrics.RECORD_FLOW_INVARIANTS_TOTAL,
        "bioetl_stage_records_total": _metrics.STAGE_RECORDS_TOTAL,
        "bioetl_batch_lifecycle_events_total": _metrics.BATCH_LIFECYCLE_EVENTS_TOTAL,
        "bioetl_batch_lifecycle_records_total": _metrics.BATCH_LIFECYCLE_RECORDS_TOTAL,
        "bioetl_composite_phase_records_total": _metrics.COMPOSITE_PHASE_RECORDS_TOTAL,
        "bioetl_composite_phase_errors_total": _metrics.COMPOSITE_PHASE_ERRORS_TOTAL,
        "bioetl_composite_phase_loss_total": _metrics.COMPOSITE_PHASE_LOSS_TOTAL,
        "bioetl_composite_phase_retries_total": _metrics.COMPOSITE_PHASE_RETRIES_TOTAL,
        "bioetl_errors_total": _metrics.ERRORS_TOTAL,
        "bioetl_filter_ids_loaded_total": _metrics.FILTER_IDS_LOADED_TOTAL,
        "bioetl_filter_ids_duplicates_total": _metrics.FILTER_IDS_DUPLICATES_TOTAL,
        "bioetl_pipeline_runs_total": _metrics.PIPELINE_RUNS_TOTAL,
        "bioetl_postrun_phase_events_total": _metrics.POSTRUN_PHASE_EVENTS_TOTAL,
        "bioetl_shutdown_initiated": _metrics.SHUTDOWN_INITIATED,
        "bioetl_shutdown_completed": _metrics.SHUTDOWN_COMPLETED,
        "bioetl_filter_combinations_loaded_total": _metrics.FILTER_COMBINATIONS_LOADED_TOTAL,
        "bioetl_transform_errors_total": _metrics.TRANSFORM_ERRORS_TOTAL,
        "bioetl_structural_policy_events_total": _metrics.STRUCTURAL_POLICY_EVENTS_TOTAL,
        "bioetl_structural_policy_shadow_comparisons_total": (
            _metrics.STRUCTURAL_POLICY_SHADOW_COMPARISONS_TOTAL
        ),
        "bioetl_control_plane_manifest_writes_total": _metrics.CONTROL_PLANE_MANIFEST_WRITES_TOTAL,
        "bioetl_control_plane_ledger_appends_total": _metrics.CONTROL_PLANE_LEDGER_APPENDS_TOTAL,
        "bioetl_control_plane_terminal_events_total": _metrics.CONTROL_PLANE_TERMINAL_EVENTS_TOTAL,
        "bioetl_control_plane_reads_total": _metrics.CONTROL_PLANE_READS_TOTAL,
        "bioetl_control_plane_lifecycle_deleted_total": _metrics.CONTROL_PLANE_LIFECYCLE_DELETED_TOTAL,
        "bioetl_control_plane_lifecycle_apply_total": _metrics.CONTROL_PLANE_LIFECYCLE_APPLY_TOTAL,
        "bioetl_checkpoint_compatibility_events_total": _metrics.CHECKPOINT_COMPATIBILITY_EVENTS_TOTAL,
        "bioetl_checkpoint_load_events_total": _metrics.CHECKPOINT_LOAD_EVENTS_TOTAL,
        "bioetl_checkpoint_operator_operations_total": _metrics.CHECKPOINT_OPERATOR_OPERATIONS_TOTAL,
        "bioetl_checkpoint_save_events_total": _metrics.CHECKPOINT_SAVE_EVENTS_TOTAL,
        "bioetl_memory_pressure_events_total": _metrics.MEMORY_PRESSURE_EVENTS_TOTAL,
        "bioetl_memory_batch_resize_events_total": _metrics.MEMORY_BATCH_RESIZE_EVENTS_TOTAL,
        "bioetl_memory_monitor_fallback_events_total": _metrics.MEMORY_MONITOR_FALLBACK_EVENTS_TOTAL,
        "bioetl_traced_runs_total": _metrics.TRACED_RUNS_TOTAL,
        "bioetl_replay_reconstructability_events_total": (
            _metrics.REPLAY_RECONSTRUCTABILITY_EVENTS_TOTAL
        ),
        "bioetl_replay_drift_events_total": _metrics.REPLAY_DRIFT_EVENTS_TOTAL,
        "bioetl_metrics_publication_events_total": _metrics.METRICS_PUBLICATION_EVENTS_TOTAL,
        "bioetl_publication_raw_vocab_unknown_total": (
            _metrics.PUBLICATION_RAW_VOCAB_UNKNOWN_TOTAL
        ),
        "bioetl_workflow_runs_total": _metrics.WORKFLOW_RUNS_TOTAL,
        "bioetl_workflow_step_events_total": _metrics.WORKFLOW_STEP_EVENTS_TOTAL,
        "bioetl_workflow_reconciliation_rows_scanned_total": (
            _metrics.WORKFLOW_RECONCILIATION_ROWS_SCANNED_TOTAL
        ),
        "bioetl_workflow_reconciliation_rows_retained_total": (
            _metrics.WORKFLOW_RECONCILIATION_ROWS_RETAINED_TOTAL
        ),
        "bioetl_workflow_reconciliation_rows_deleted_total": (
            _metrics.WORKFLOW_RECONCILIATION_ROWS_DELETED_TOTAL
        ),
        "bioetl_workflow_row_reconciliation_left_rows_total": (
            _metrics.WORKFLOW_ROW_RECONCILIATION_LEFT_ROWS_TOTAL
        ),
        "bioetl_workflow_row_reconciliation_right_rows_total": (
            _metrics.WORKFLOW_ROW_RECONCILIATION_RIGHT_ROWS_TOTAL
        ),
        "bioetl_workflow_row_reconciliation_kept_rows_total": (
            _metrics.WORKFLOW_ROW_RECONCILIATION_KEPT_ROWS_TOTAL
        ),
        "bioetl_workflow_row_reconciliation_excluded_rows_total": (
            _metrics.WORKFLOW_ROW_RECONCILIATION_EXCLUDED_ROWS_TOTAL
        ),
    },
    gauges={
        "bioetl_memory_pressure_state": _metrics.MEMORY_PRESSURE_STATE,
        "bioetl_control_plane_lifecycle_delete_candidates": _metrics.CONTROL_PLANE_LIFECYCLE_DELETE_CANDIDATES,
        "bioetl_observability_runtime_status": _metrics.OBSERVABILITY_RUNTIME_STATUS,
        "bioetl_pipeline_stage_expected": _metrics.PIPELINE_STAGE_EXPECTED,
        "bioetl_stage_backlog_records": _metrics.STAGE_BACKLOG_RECORDS,
        "bioetl_stage_lag_seconds": _metrics.STAGE_LAG_SECONDS,
        "bioetl_checkpoint_saved_at_seconds": _metrics.CHECKPOINT_SAVED_AT_SECONDS,
        "bioetl_replay_lag_seconds": _metrics.REPLAY_LAG_SECONDS,
        "bioetl_workflow_current_status": _metrics.WORKFLOW_CURRENT_STATUS,
        "bioetl_workflow_expected": WORKFLOW_EXPECTED,
        "bioetl_workflow_pipeline_expected": WORKFLOW_PIPELINE_EXPECTED,
    },
    histograms={
        "bioetl_pipeline_duration_seconds": _metrics.PIPELINE_DURATION_SECONDS,
        "bioetl_batch_size_records": _metrics.BATCH_SIZE_RECORDS,
        "bioetl_phase_duration_seconds": _metrics.PHASE_DURATION_SECONDS,
        "bioetl_postrun_phase_duration_seconds": _metrics.POSTRUN_PHASE_DURATION_SECONDS,
        "bioetl_transform_duration_seconds": _metrics.TRANSFORM_DURATION_SECONDS,
        "bioetl_control_plane_manifest_write_duration_seconds": (
            _metrics.CONTROL_PLANE_MANIFEST_WRITE_DURATION_SECONDS
        ),
        "bioetl_control_plane_ledger_append_duration_seconds": (
            _metrics.CONTROL_PLANE_LEDGER_APPEND_DURATION_SECONDS
        ),
        "bioetl_control_plane_read_duration_seconds": _metrics.CONTROL_PLANE_READ_DURATION_SECONDS,
        "bioetl_checkpoint_operator_duration_seconds": _metrics.CHECKPOINT_OPERATOR_DURATION_SECONDS,
        "bioetl_checkpoint_save_duration_seconds": _metrics.CHECKPOINT_SAVE_DURATION_SECONDS,
        "bioetl_workflow_step_duration_seconds": _metrics.WORKFLOW_STEP_DURATION_SECONDS,
    },
)

STORAGE_MEDALLION_REGISTRY = MetricRegistryFamily(
    family="storage_medallion",
    counters={
        "bioetl_audit_write_events_total": _metrics.AUDIT_WRITE_EVENTS_TOTAL,
        "bioetl_audit_query_events_total": _metrics.AUDIT_QUERY_EVENTS_TOTAL,
        "bioetl_vacuum_files_removed_total": _metrics.VACUUM_FILES_REMOVED_TOTAL,
        "bioetl_storage_optimization_total": _metrics.STORAGE_OPTIMIZATION_TOTAL,
        "bioetl_bronze_write_attempts_total": _metrics.BRONZE_WRITE_ATTEMPTS_TOTAL,
        "bioetl_bronze_records_written_total": _metrics.BRONZE_RECORDS_WRITTEN_TOTAL,
        "bioetl_bronze_bytes_written_total": _metrics.BRONZE_BYTES_WRITTEN_TOTAL,
        "bioetl_bronze_files_removed_total": _metrics.BRONZE_FILES_REMOVED_TOTAL,
        "bioetl_bronze_bytes_freed_total": _metrics.BRONZE_BYTES_FREED_TOTAL,
        "bioetl_policy_violations_total": _metrics.POLICY_VIOLATIONS_TOTAL,
        "bioetl_silver_csv_export_start_total": _metrics.SILVER_CSV_EXPORT_START_TOTAL,
        "bioetl_silver_csv_export_success_total": _metrics.SILVER_CSV_EXPORT_SUCCESS_TOTAL,
        "bioetl_silver_csv_export_failures_total": _metrics.SILVER_CSV_EXPORT_FAILURES_TOTAL,
        "bioetl_silver_vacuum_start_total": _metrics.SILVER_VACUUM_START_TOTAL,
        "bioetl_silver_vacuum_success_total": _metrics.SILVER_VACUUM_SUCCESS_TOTAL,
        "bioetl_silver_optimize_start_total": _metrics.SILVER_OPTIMIZE_START_TOTAL,
        "bioetl_silver_optimize_success_total": _metrics.SILVER_OPTIMIZE_SUCCESS_TOTAL,
        "bioetl_silver_merge_retries_total": _metrics.SILVER_MERGE_RETRIES_TOTAL,
        "bioetl_silver_merge_failures_total": _metrics.SILVER_MERGE_FAILURES_TOTAL,
        "bioetl_silver_validation_failures_total": _metrics.SILVER_VALIDATION_FAILURES_TOTAL,
        "bioetl_gold_write_attempts_total": _metrics.GOLD_WRITE_ATTEMPTS_TOTAL,
        "bioetl_gold_write_outcomes_total": _metrics.GOLD_WRITE_OUTCOMES_TOTAL,
        "bioetl_gold_validation_failures_total": _metrics.GOLD_VALIDATION_FAILURES_TOTAL,
        "bioetl_gold_lifecycle_state_total": _metrics.GOLD_LIFECYCLE_STATE_TOTAL,
        "bioetl_metadata_write_retries_total": _metrics.METADATA_WRITE_RETRIES_TOTAL,
        "bioetl_metadata_write_outcomes_total": _metrics.METADATA_WRITE_OUTCOMES_TOTAL,
        "bioetl_quarantine_records_total": _metrics.QUARANTINE_RECORDS_TOTAL,
        "bioetl_output_artifact_publication_events_total": (
            _metrics.OUTPUT_ARTIFACT_PUBLICATION_EVENTS_TOTAL
        ),
        "bioetl_silver_filter_rejections_total": _metrics.SILVER_FILTER_REJECTIONS_TOTAL,
        "bioetl_lineage_fragments_emitted_total": _metrics.LINEAGE_FRAGMENTS_EMITTED_TOTAL,
        "bioetl_lineage_refs_missing_total": _metrics.LINEAGE_REFS_MISSING_TOTAL,
        "bioetl_composite_source_selection_total": _metrics.COMPOSITE_SOURCE_SELECTION_TOTAL,
        "bioetl_quarantine_operator_operations_total": _metrics.QUARANTINE_OPERATOR_OPERATIONS_TOTAL,
    },
    gauges={
        "bioetl_silver_vacuum_files_removed": _metrics.SILVER_VACUUM_FILES_REMOVED,
    },
    histograms={
        "bioetl_audit_write_duration_seconds": _metrics.AUDIT_WRITE_DURATION_SECONDS,
        "bioetl_audit_query_duration_seconds": _metrics.AUDIT_QUERY_DURATION_SECONDS,
        "bioetl_bronze_write_duration_seconds": _metrics.BRONZE_WRITE_DURATION_SECONDS,
        "bioetl_bronze_write_total_duration_seconds": _metrics.BRONZE_WRITE_TOTAL_DURATION_SECONDS,
        "bioetl_gold_write_duration_seconds": _metrics.GOLD_WRITE_DURATION_SECONDS,
        "bioetl_quarantine_operator_duration_seconds": _metrics.QUARANTINE_OPERATOR_DURATION_SECONDS,
    },
)

HTTP_ADAPTER_REGISTRY = MetricRegistryFamily(
    family="http_adapters",
    counters={
        "bioetl_adapter_requests_total": _metrics.ADAPTER_REQUESTS_TOTAL,
        "bioetl_adapter_dropped_duplicates_total": _metrics.ADAPTER_DROPPED_DUPLICATES_TOTAL,
        "bioetl_adapter_fallback_attempts_total": _metrics.ADAPTER_FALLBACK_ATTEMPTS_TOTAL,
        "bioetl_adapter_fallback_hits_total": _metrics.ADAPTER_FALLBACK_HITS_TOTAL,
        "bioetl_adapter_error_taxonomy_total": _metrics.ADAPTER_ERROR_TAXONOMY_TOTAL,
        "bioetl_data_source_retries_total": _metrics.DATA_SOURCE_RETRIES_TOTAL,
        "bioetl_data_source_retry_exhausted_total": _metrics.DATA_SOURCE_RETRY_EXHAUSTED_TOTAL,
        "bioetl_http_retries_total": _metrics.HTTP_RETRIES_TOTAL,
        "bioetl_http_retry_budget_exhausted_total": _metrics.HTTP_RETRY_BUDGET_EXHAUSTED_TOTAL,
        "bioetl_http_request_errors_total": _metrics.HTTP_REQUEST_ERRORS_TOTAL,
    },
    gauges={
        "bioetl_provider_health_status": _metrics.PROVIDER_HEALTH_STATUS,
        "bioetl_adapter_fallback_hit_rate": _metrics.ADAPTER_FALLBACK_HIT_RATE,
        "bioetl_rate_limiter_tokens_available": _metrics.RATE_LIMITER_TOKENS_AVAILABLE,
    },
    histograms={
        "bioetl_adapter_request_duration_seconds": _metrics.ADAPTER_REQUEST_DURATION_SECONDS,
        "bioetl_adapter_batch_size": _metrics.ADAPTER_BATCH_SIZE,
        "bioetl_http_request_duration_seconds": _metrics.HTTP_REQUEST_DURATION_SECONDS,
        "bioetl_rate_limiter_wait_seconds": _metrics.RATE_LIMITER_WAIT_SECONDS,
    },
)

DQ_VALIDATION_REGISTRY = MetricRegistryFamily(
    family="dq_validation",
    counters={
        "bioetl_dq_context_build_failures_total": _metrics.DQ_CONTEXT_BUILD_FAILURES_TOTAL,
        "bioetl_dq_dispositions_total": _metrics.DQ_DISPOSITIONS_TOTAL,
        "bioetl_dq_records_quarantined_total": _metrics.DQ_RECORDS_QUARANTINED_TOTAL,
        "bioetl_dq_anomaly_detected": _metrics.DQ_ANOMALY_DETECTED,
        "bioetl_dq_baseline_updated": _metrics.DQ_BASELINE_UPDATED,
        "bioetl_dq_monitor_disabled_total": _metrics.DQ_MONITOR_DISABLED_TOTAL,
        "bioetl_dq_report_generated_total": _metrics.DQ_REPORT_GENERATED_TOTAL,
        "bioetl_dq_report_skipped_total": _metrics.DQ_REPORT_SKIPPED_TOTAL,
        "bioetl_dq_soft_threshold_exceeded": _metrics.DQ_SOFT_THRESHOLD_EXCEEDED,
        "bioetl_dq_validation_failures_total": _metrics.DQ_VALIDATION_FAILURES_TOTAL,
        "bioetl_dq_check_failures_total": _metrics.DQ_CHECK_FAILURES_TOTAL,
        "bioetl_observability_events_total": _metrics.OBSERVABILITY_EVENTS_TOTAL,
    },
    gauges={
        "bioetl_dq_baseline_samples": _metrics.DQ_BASELINE_SAMPLES,
        "bioetl_dq_monitor_enabled": _metrics.DQ_MONITOR_ENABLED,
        "bioetl_dq_validation_record_count": _metrics.DQ_VALIDATION_RECORD_COUNT,
        "bioetl_dq_validation_score": _metrics.DQ_VALIDATION_SCORE,
        "bioetl_data_freshness_seconds": _metrics.DATA_FRESHNESS_SECONDS,
    },
    histograms={
        "bioetl_dq_check_duration_ms": _metrics.DQ_CHECK_DURATION_MS,
    },
)

SYSTEM_PROCESS_REGISTRY = MetricRegistryFamily(
    family="system_process",
    counters={
        "bioetl_circuit_breaker_trips_total": _metrics.CIRCUIT_BREAKER_TRIPS_TOTAL,
        "bioetl_circuit_breaker_open_total": _metrics.CIRCUIT_BREAKER_OPEN_TOTAL,
        "bioetl_circuit_breaker_success_total": _metrics.CIRCUIT_BREAKER_SUCCESS_TOTAL,
        "bioetl_circuit_breaker_failure_total": _metrics.CIRCUIT_BREAKER_FAILURE_TOTAL,
        "bioetl_health_check_degraded_total": _metrics.HEALTH_CHECK_DEGRADED_TOTAL,
        "bioetl_health_check_success_total": _metrics.HEALTH_CHECK_SUCCESS_TOTAL,
        "bioetl_health_check_failures_total": _metrics.HEALTH_CHECK_FAILURES_TOTAL,
        "bioetl_probe_mode_fallback_total": _metrics.PROBE_MODE_FALLBACK_TOTAL,
    },
    gauges={
        "bioetl_circuit_breaker_state": _metrics.CIRCUIT_BREAKER_STATE,
        "bioetl_pipeline_health_check_passed": _metrics.PIPELINE_HEALTH_CHECK_PASSED,
        "bioetl_infrastructure_validated": _metrics.INFRASTRUCTURE_VALIDATED,
        "bioetl_health_check_status": _metrics.HEALTH_CHECK_STATUS,
        "bioetl_health_check_mode_status": _metrics.HEALTH_CHECK_MODE_STATUS,
    },
    histograms={
        "bioetl_health_check_duration_seconds": _metrics.HEALTH_CHECK_DURATION_SECONDS,
        "bioetl_health_check_latency_seconds": _metrics.HEALTH_CHECK_LATENCY_SECONDS,
        "bioetl_health_check_mode_latency_seconds": _metrics.HEALTH_CHECK_MODE_LATENCY_SECONDS,
    },
)

METRIC_REGISTRY_FAMILIES: tuple[MetricRegistryFamily, ...] = (
    PIPELINE_RUNTIME_REGISTRY,
    STORAGE_MEDALLION_REGISTRY,
    HTTP_ADAPTER_REGISTRY,
    DQ_VALIDATION_REGISTRY,
    SYSTEM_PROCESS_REGISTRY,
)

METRIC_REGISTRY_INVENTORY: dict[str, dict[str, tuple[str, ...]]] = {
    family.family: {
        "counters": tuple(family.counters.keys()),
        "gauges": tuple(family.gauges.keys()),
        "histograms": tuple(family.histograms.keys()),
    }
    for family in METRIC_REGISTRY_FAMILIES
}


def build_counter_registry() -> dict[str, PrometheusCounter]:
    """Merge grouped counter registries into one public mapping."""
    merged: dict[str, PrometheusCounter] = {}
    for family in METRIC_REGISTRY_FAMILIES:
        merged.update(family.counters)
    return merged


def build_gauge_registry() -> dict[str, PrometheusGauge]:
    """Merge grouped gauge registries into one public mapping."""
    merged: dict[str, PrometheusGauge] = {}
    for family in METRIC_REGISTRY_FAMILIES:
        merged.update(family.gauges)
    return merged


def build_histogram_registry() -> dict[str, PrometheusHistogram]:
    """Merge grouped histogram registries into one public mapping."""
    merged: dict[str, PrometheusHistogram] = {}
    for family in METRIC_REGISTRY_FAMILIES:
        merged.update(family.histograms)
    return merged


COUNTERS = build_counter_registry()
GAUGES = build_gauge_registry()
HISTOGRAMS = build_histogram_registry()

REGISTERED_PROMETHEUS_METRIC_NAMES = frozenset(
    set(COUNTERS) | set(GAUGES) | set(HISTOGRAMS)
)

__all__ = [
    "COUNTERS",
    "DQ_VALIDATION_REGISTRY",
    "GAUGES",
    "HISTOGRAMS",
    "HTTP_ADAPTER_REGISTRY",
    "METRIC_REGISTRY_FAMILIES",
    "METRIC_REGISTRY_INVENTORY",
    "PIPELINE_RUNTIME_REGISTRY",
    "REGISTERED_PROMETHEUS_METRIC_NAMES",
    "STORAGE_MEDALLION_REGISTRY",
    "SYSTEM_PROCESS_REGISTRY",
    "MetricRegistryFamily",
    "build_counter_registry",
    "build_gauge_registry",
    "build_histogram_registry",
]
