"""Core pipeline, DQ, lifecycle-adjacent Prometheus metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

from bioetl.infrastructure.observability.circuit_breaker_mapping import (
    CIRCUIT_BREAKER_STATE_DESCRIPTION,
)

__all__ = [
    "BATCH_SIZE_RECORDS",
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
    "DQ_MONITOR_ENABLED",
    "DQ_RECORDS_QUARANTINED_TOTAL",
    "DQ_VALIDATION_FAILURES_TOTAL",
    "DQ_VALIDATION_RECORD_COUNT",
    "DQ_VALIDATION_SCORE",
    "ERRORS_TOTAL",
    "FILTER_IDS_DUPLICATES_TOTAL",
    "FILTER_IDS_LOADED_TOTAL",
    "PIPELINE_DURATION_SECONDS",
    "QUARANTINE_OPERATOR_DURATION_SECONDS",
    "QUARANTINE_OPERATOR_OPERATIONS_TOTAL",
    "QUARANTINE_RECORDS_TOTAL",
    "RECORDS_PROCESSED_TOTAL",
    "RECORD_FLOW_RECORDS_TOTAL",
    "SILVER_FILTER_REJECTIONS_TOTAL",
    "VACUUM_FILES_REMOVED_TOTAL",
]

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
