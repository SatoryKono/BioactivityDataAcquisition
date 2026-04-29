"""Core pipeline, DQ, lifecycle-adjacent Prometheus metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

from bioetl.infrastructure.observability.circuit_breaker_mapping import (
    CIRCUIT_BREAKER_STATE_DESCRIPTION,
)

__all__ = sorted(
    [
        "BATCH_LIFECYCLE_EVENTS_TOTAL",
        "BATCH_LIFECYCLE_RECORDS_TOTAL",
        "BATCH_SIZE_RECORDS",
        "COMPOSITE_PHASE_ERRORS_TOTAL",
        "COMPOSITE_PHASE_LOSS_TOTAL",
        "COMPOSITE_PHASE_RECORDS_TOTAL",
        "COMPOSITE_PHASE_RETRIES_TOTAL",
        "CIRCUIT_BREAKER_FAILURE_TOTAL",
        "CIRCUIT_BREAKER_OPEN_TOTAL",
        "CIRCUIT_BREAKER_STATE",
        "CIRCUIT_BREAKER_SUCCESS_TOTAL",
        "CIRCUIT_BREAKER_TRIPS_TOTAL",
        "DATA_FRESHNESS_SECONDS",
        "DQ_ANOMALY_DETECTED",
        "DQ_BASELINE_SAMPLES",
        "DQ_BASELINE_UPDATED",
        "DQ_CHECK_DURATION_MS",
        "DQ_CHECK_FAILURES_TOTAL",
        "DQ_DISPOSITIONS_TOTAL",
        "DQ_MONITOR_DISABLED_TOTAL",
        "DQ_MONITOR_ENABLED",
        "DQ_RECORDS_QUARANTINED_TOTAL",
        "DQ_VALIDATION_FAILURES_TOTAL",
        "DQ_VALIDATION_RECORD_COUNT",
        "DQ_VALIDATION_SCORE",
        "ERRORS_TOTAL",
        "FILTER_IDS_DUPLICATES_TOTAL",
        "FILTER_IDS_LOADED_TOTAL",
        "METRICS_PUBLICATION_EVENTS_TOTAL",
        "OBSERVABILITY_RUNTIME_STATUS",
        "OUTPUT_ARTIFACT_PUBLICATION_EVENTS_TOTAL",
        "PIPELINE_DURATION_SECONDS",
        "QUARANTINE_OPERATOR_DURATION_SECONDS",
        "QUARANTINE_OPERATOR_OPERATIONS_TOTAL",
        "QUARANTINE_RECORDS_TOTAL",
        "RECORD_FLOW_RECORDS_TOTAL",
        "RECORD_FLOW_INVARIANTS_TOTAL",
        "RECORDS_PROCESSED_TOTAL",
        "SILVER_FILTER_REJECTIONS_TOTAL",
        "STAGE_BACKLOG_RECORDS",
        "STAGE_LAG_SECONDS",
        "STAGE_RECORDS_TOTAL",
        "VACUUM_FILES_REMOVED_TOTAL",
    ]
)

PIPELINE_DURATION_SECONDS = Histogram(
    "bioetl_pipeline_duration_seconds",
    "Duration of pipeline runs in seconds",
    ["pipeline", "stage", "status", "run_type"],
)

RECORDS_PROCESSED_TOTAL = Counter(
    "bioetl_records_processed_total",
    "Total number of records processed by the pipeline",
    ["pipeline", "stage", "run_type"],
)

RECORD_FLOW_RECORDS_TOTAL = Counter(
    "bioetl_record_flow_records_total",
    "Total records observed in the bounded pipeline flow projection",
    ["pipeline", "run_type", "flow_stage"],
)

RECORD_FLOW_INVARIANTS_TOTAL = Counter(
    "bioetl_record_flow_invariants_total",
    "Terminal invariant outcomes derived from bounded record-flow projections",
    ["pipeline", "run_type", "invariant", "status"],
)

STAGE_RECORDS_TOTAL = Counter(
    "bioetl_stage_records_total",
    "Total records observed in the canonical stage-model projection",
    ["pipeline", "run_type", "stage", "outcome"],
)

STAGE_BACKLOG_RECORDS = Gauge(
    "bioetl_stage_backlog_records",
    "Current bounded unresolved record backlog projected by canonical stage",
    ["pipeline", "run_type", "stage"],
)

STAGE_LAG_SECONDS = Gauge(
    "bioetl_stage_lag_seconds",
    "Current bounded unresolved stage lag in seconds for canonical stage backlogs",
    ["pipeline", "run_type", "stage"],
)

BATCH_LIFECYCLE_EVENTS_TOTAL = Counter(
    "bioetl_batch_lifecycle_events_total",
    "Total bounded batch lifecycle events projected by layer stage and outcome status",
    ["pipeline", "run_type", "event", "stage", "status"],
)

BATCH_LIFECYCLE_RECORDS_TOTAL = Counter(
    "bioetl_batch_lifecycle_records_total",
    "Total records associated with bounded batch lifecycle event projections",
    ["pipeline", "run_type", "event", "stage", "status"],
)

OUTPUT_ARTIFACT_PUBLICATION_EVENTS_TOTAL = Counter(
    "bioetl_output_artifact_publication_events_total",
    "Total bounded output artifact publication outcomes by stage and status",
    ["pipeline", "stage", "status"],
)

COMPOSITE_PHASE_RECORDS_TOTAL = Counter(
    "bioetl_composite_phase_records_total",
    "Total bounded record projections across canonical composite phases",
    ["pipeline", "phase", "outcome"],
)

COMPOSITE_PHASE_ERRORS_TOTAL = Counter(
    "bioetl_composite_phase_errors_total",
    "Total bounded error projections across canonical composite phases",
    ["pipeline", "phase", "error_kind"],
)

COMPOSITE_PHASE_LOSS_TOTAL = Counter(
    "bioetl_composite_phase_loss_total",
    "Total bounded loss projections across canonical composite phases",
    ["pipeline", "phase", "loss_kind"],
)

COMPOSITE_PHASE_RETRIES_TOTAL = Counter(
    "bioetl_composite_phase_retries_total",
    "Total bounded retry or resume projections across canonical composite phases",
    ["pipeline", "phase", "retry_kind"],
)

ERRORS_TOTAL = Counter(
    "bioetl_errors_total",
    "Total number of errors encountered",
    ["pipeline", "stage", "error_code"],
)

BATCH_SIZE_RECORDS = Histogram(
    "bioetl_batch_size_records",
    "Distribution of batch sizes (number of records)",
    ["pipeline", "stage"],
    buckets=[100, 500, 1000, 5000, 10000, 50000],
)

FILTER_IDS_LOADED_TOTAL = Counter(
    "bioetl_filter_ids_loaded_total",
    "Total unique IDs loaded from input filter source",
    ["pipeline", "source_file"],
)

FILTER_IDS_DUPLICATES_TOTAL = Counter(
    "bioetl_filter_ids_duplicates_total",
    "Total duplicate IDs found in input filter source",
    ["pipeline", "source_file"],
)

DQ_RECORDS_QUARANTINED_TOTAL = Counter(
    "bioetl_dq_records_quarantined_total",
    "Total number of records quarantined due to data quality issues",
    ["pipeline", "error_type", "run_type"],
)

DQ_DISPOSITIONS_TOTAL = Counter(
    "bioetl_dq_dispositions_total",
    "Total bounded DQ disposition events correlated with terminal run outcomes",
    ["pipeline", "stage", "disposition", "terminal_status"],
)

QUARANTINE_RECORDS_TOTAL = Counter(
    "bioetl_quarantine_records_total",
    "Total number of records written to quarantine",
    ["pipeline", "reason"],
)

QUARANTINE_OPERATOR_OPERATIONS_TOTAL = Counter(
    "bioetl_quarantine_operator_operations_total",
    "Total number of quarantine explorer/admin operations by operation and status",
    ["operation", "status"],
)

QUARANTINE_OPERATOR_DURATION_SECONDS = Histogram(
    "bioetl_quarantine_operator_duration_seconds",
    "Duration of quarantine explorer/admin operations in seconds",
    ["operation", "status"],
)

SILVER_FILTER_REJECTIONS_TOTAL = Counter(
    "bioetl_silver_filter_rejections_total",
    "Total number of Silver filter rejections with bounded analytical labels",
    ["pipeline", "run_type", "reason_code", "rule_type", "field"],
)

DQ_VALIDATION_FAILURES_TOTAL = Counter(
    "bioetl_dq_validation_failures_total",
    "Total number of DQ validation threshold failures",
    ["pipeline", "stage", "severity"],
)

DQ_CHECK_FAILURES_TOTAL = Counter(
    "bioetl_dq_check_failures_total",
    "Total failed or warning DQ checks by check type",
    ["pipeline", "stage", "check_type", "severity"],
)

CIRCUIT_BREAKER_STATE = Gauge(
    "bioetl_circuit_breaker_state",
    CIRCUIT_BREAKER_STATE_DESCRIPTION,
    ["adapter"],
)

CIRCUIT_BREAKER_OPEN_TOTAL = Counter(
    "bioetl_circuit_breaker_open_total",
    "Total calls rejected while the circuit breaker is open",
    ["adapter"],
)

CIRCUIT_BREAKER_TRIPS_TOTAL = Counter(
    "bioetl_circuit_breaker_trips_total",
    "Total number of times the circuit breaker has tripped (opened)",
    ["adapter"],
)

CIRCUIT_BREAKER_SUCCESS_TOTAL = Counter(
    "bioetl_circuit_breaker_success_total",
    "Total successful calls through the circuit breaker",
    ["adapter"],
)

CIRCUIT_BREAKER_FAILURE_TOTAL = Counter(
    "bioetl_circuit_breaker_failure_total",
    "Total failed calls through the circuit breaker",
    ["adapter"],
)

VACUUM_FILES_REMOVED_TOTAL = Counter(
    "bioetl_vacuum_files_removed_total",
    "Total files removed by vacuum operations",
    ["table", "layer"],
)

DQ_VALIDATION_SCORE = Gauge(
    "bioetl_dq_validation_score",
    "Data quality validation score (0.0-1.0, where 1.0 = all records valid)",
    ["pipeline", "entity"],
)

DQ_VALIDATION_RECORD_COUNT = Gauge(
    "bioetl_dq_validation_record_count",
    "Record count associated with the latest entity-level DQ validation score",
    ["pipeline", "entity"],
)

DATA_FRESHNESS_SECONDS = Gauge(
    "bioetl_data_freshness_seconds",
    "Unix timestamp in seconds for the last successful data ingestion "
    "for pipeline/entity; consumers derive lag via time() - metric",
    ["pipeline", "entity"],
)

DQ_ANOMALY_DETECTED = Counter(
    "bioetl_dq_anomaly_detected",
    "Total number of data quality anomalies detected",
    ["pipeline", "metric", "severity", "anomaly_type"],
)

DQ_CHECK_DURATION_MS = Histogram(
    "bioetl_dq_check_duration_ms",
    "Duration of data quality check in milliseconds",
    ["pipeline"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
)

DQ_MONITOR_ENABLED = Gauge(
    "bioetl_dq_monitor_enabled",
    "Whether anomaly detection is configured for the pipeline/entity (1 enabled, 0 disabled)",
    ["pipeline", "entity"],
)

DQ_BASELINE_UPDATED = Counter(
    "bioetl_dq_baseline_updated",
    "Number of times DQ monitor baseline was updated",
    ["pipeline", "metric"],
)

DQ_MONITOR_DISABLED_TOTAL = Counter(
    "bioetl_dq_monitor_disabled_total",
    "Total DQ evaluations executed without an anomaly monitor configured",
    ["pipeline", "entity"],
)

DQ_BASELINE_SAMPLES = Gauge(
    "bioetl_dq_baseline_samples",
    "Current number of samples in DQ baseline",
    ["pipeline", "metric"],
)

METRICS_PUBLICATION_EVENTS_TOTAL = Counter(
    "bioetl_metrics_publication_events_total",
    "Total best-effort metrics publication attempts by target and status",
    ["pipeline", "run_type", "target", "status"],
)

OBSERVABILITY_RUNTIME_STATUS = Gauge(
    "bioetl_observability_runtime_status",
    "Current observability component mode for the active pipeline runtime",
    ["pipeline", "component", "mode"],
)
