"""Prometheus Metrics for BioETL."""

from __future__ import annotations

from bioetl.infrastructure.observability.metrics_export_names import (
    METRICS_DEFINITION_EXPORT_NAMES,
)

__all__ = list(METRICS_DEFINITION_EXPORT_NAMES)

from prometheus_client import Counter, Gauge, Histogram

from bioetl.infrastructure.observability.circuit_breaker_mapping import (
    CIRCUIT_BREAKER_STATE_DESCRIPTION,
)

# Generic pipeline metrics
PIPELINE_DURATION_SECONDS = Histogram(
    "bioetl_pipeline_duration_seconds",
    "Duration of pipeline runs in seconds",
    ["pipeline", "stage", "status", "run_type"],
)

RECORDS_PROCESSED_TOTAL = Counter(
    "bioetl_records_processed_total",
    "Total number of records processed by the pipeline",
    ["pipeline", "stage", "run_type"],  # stage: bronze, silver, gold, quarantined
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

# Input filter metrics
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

# Data Quality metrics
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

DQ_VALIDATION_FAILURES_TOTAL = Counter(
    "bioetl_dq_validation_failures_total",
    "Total number of DQ validation threshold failures",
    ["pipeline", "stage", "severity"],
)

# Circuit Breaker metrics (per ADR-007)
CIRCUIT_BREAKER_STATE = Gauge(
    "bioetl_circuit_breaker_state",
    CIRCUIT_BREAKER_STATE_DESCRIPTION,
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

# VACUUM metrics
VACUUM_FILES_REMOVED_TOTAL = Counter(
    "bioetl_vacuum_files_removed_total",
    "Total files removed by vacuum operations",
    ["table", "layer"],
)

VACUUM_DURATION_SECONDS = Histogram(
    "bioetl_vacuum_duration_seconds",
    "Duration of vacuum operations",
    ["table"],
)

# Archive metrics
ARCHIVE_FILES_TOTAL = Counter(
    "bioetl_archive_files_total",
    "Total files archived",
    ["table", "target"],
)

ARCHIVE_DURATION_SECONDS = Histogram(
    "bioetl_archive_duration_seconds",
    "Duration of archive operations",
    ["table"],
)

# Data Quality Monitor metrics
DQ_VALIDATION_SCORE = Gauge(
    "bioetl_dq_validation_score",
    "Data quality validation score (0.0-1.0, where 1.0 = all records valid)",
    ["pipeline", "entity"],
)

DATA_FRESHNESS_SECONDS = Gauge(
    "bioetl_data_freshness_seconds",
    "Seconds since last successful data ingestion for pipeline/entity",
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

DQ_BASELINE_UPDATED = Counter(
    "bioetl_dq_baseline_updated",
    "Number of times DQ monitor baseline was updated",
    ["pipeline", "metric"],
)

DQ_BASELINE_SAMPLES = Gauge(
    "bioetl_dq_baseline_samples",
    "Current number of samples in DQ baseline",
    ["pipeline", "metric"],
)

# =============================================================================
# Health Check metrics (Unified Observability Contract)
# =============================================================================

PIPELINE_HEALTH_CHECK_PASSED = Gauge(
    "bioetl_pipeline_health_check_passed",
    "Health check status for pipeline components (1=passed, 0=failed)",
    ["pipeline", "component"],
)

INFRASTRUCTURE_VALIDATED = Gauge(
    "bioetl_infrastructure_validated",
    "Infrastructure validation status (1=validated, 0=not validated)",
    ["pipeline", "run_id"],
)

HEALTH_CHECK_DURATION_SECONDS = Histogram(
    "bioetl_health_check_duration_seconds",
    "Duration of health check operations in seconds",
    ["pipeline"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

HEALTH_CHECK_STATUS = Gauge(
    "bioetl_health_check_status",
    "Health check status per component (0=unknown, 1=healthy, 2=degraded)",
    ["component"],
)

HEALTH_CHECK_MODE_STATUS = Gauge(
    "bioetl_health_check_mode_status",
    "Health check status by mode and component (0=unknown, 1=healthy, 2=degraded)",
    ["component", "mode"],
)

HEALTH_CHECK_LATENCY_MS = Histogram(
    "bioetl_health_check_latency_ms",
    "Health check latency in milliseconds",
    ["provider"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000],
)

HEALTH_CHECK_MODE_LATENCY_MS = Histogram(
    "bioetl_health_check_mode_latency_ms",
    "Health check latency in milliseconds by health-check mode",
    ["provider", "mode"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000],
)

HEALTH_CHECK_SUCCESS_TOTAL = Counter(
    "bioetl_health_check_success_total",
    "Total successful health checks",
    ["provider"],
)

HEALTH_CHECK_FAILURES_TOTAL = Counter(
    "bioetl_health_check_failures_total",
    "Total failed health checks",
    ["provider"],
)

PROBE_MODE_FALLBACK_TOTAL = Counter(
    "bioetl_probe_mode_fallback_total",
    "Total probe-mode fallbacks that downgraded data-source health to degraded",
    ["pipeline", "component", "reason"],
)

HEALTH_CHECK_LATENCY_SECONDS = Histogram(
    "bioetl_health_check_latency_seconds",
    "Health check latency in seconds",
    ["provider"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

PREFLIGHT_MEDALLION_POLICY_VALID = Gauge(
    "bioetl_preflight_medallion_policy_valid",
    "Whether medallion policy is valid (1=valid, 0=invalid)",
    ["pipeline", "run_id"],
)

PREFLIGHT_CONFIG_ERRORS_TOTAL = Gauge(
    "bioetl_preflight_config_errors_total",
    "Number of configuration errors found during preflight",
    ["pipeline", "run_id"],
)

# =============================================================================
# Pipeline lifecycle metrics
# =============================================================================

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

# =============================================================================
# Transformer metrics
# =============================================================================

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

# =============================================================================
# DQ additional metrics
# =============================================================================

DQ_SOFT_THRESHOLD_EXCEEDED = Counter(
    "bioetl_dq_soft_threshold_exceeded",
    "Total times DQ soft threshold was exceeded",
    ["pipeline"],
)

# =============================================================================
# Shutdown metrics
# =============================================================================

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

# =============================================================================
# Storage optimization metrics
# =============================================================================

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

# =============================================================================
# Adapter / HTTP metrics
# =============================================================================

ADAPTER_REQUEST_DURATION_SECONDS = Histogram(
    "bioetl_adapter_request_duration_seconds",
    "Duration of adapter API requests in seconds",
    ["provider", "endpoint"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

ADAPTER_REQUEST_P95_SECONDS = Gauge(
    "bioetl_adapter_request_p95_seconds",
    "Rolling p95 latency of adapter requests in seconds",
    ["provider", "endpoint"],
)

ADAPTER_REQUESTS_TOTAL = Counter(
    "bioetl_adapter_requests_total",
    "Total adapter API requests",
    ["provider", "endpoint", "status"],
)

ADAPTER_BATCH_SIZE = Histogram(
    "bioetl_adapter_batch_size",
    "Distribution of adapter response batch sizes",
    ["provider", "endpoint"],
    buckets=[10, 50, 100, 500, 1000, 5000, 10000],
)

ADAPTER_DROPPED_DUPLICATES_TOTAL = Counter(
    "bioetl_adapter_dropped_duplicates_total",
    "Total duplicate records dropped by adapter dedup",
    ["provider", "entity_type"],
)

ADAPTER_FALLBACK_ATTEMPTS_TOTAL = Counter(
    "bioetl_adapter_fallback_attempts_total",
    "Total fallback resolution candidates processed by adapter flows",
    ["provider", "operation"],
)

ADAPTER_FALLBACK_HITS_TOTAL = Counter(
    "bioetl_adapter_fallback_hits_total",
    "Total records resolved via fallback paths",
    ["provider", "operation"],
)

ADAPTER_FALLBACK_HIT_RATE = Gauge(
    "bioetl_adapter_fallback_hit_rate",
    "Fallback hit-rate for adapter flows (0-1)",
    ["provider", "operation"],
)

ADAPTER_ERROR_TAXONOMY_TOTAL = Counter(
    "bioetl_adapter_error_taxonomy_total",
    "Error taxonomy counter for adapter failures",
    ["provider", "operation", "error_category", "error_type"],
)

DATA_SOURCE_RETRIES_TOTAL = Counter(
    "bioetl_data_source_retries_total",
    "Total data source retry attempts",
    ["provider", "operation"],
)

DATA_SOURCE_RETRY_EXHAUSTED_TOTAL = Counter(
    "bioetl_data_source_retry_exhausted_total",
    "Total data source retry exhaustions",
    ["provider", "operation"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "bioetl_http_request_duration_seconds",
    "Duration of HTTP requests in seconds",
    ["provider", "method", "status"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

HTTP_RETRIES_TOTAL = Counter(
    "bioetl_http_retries_total",
    "Total HTTP request retries",
    ["provider", "method"],
)

HTTP_REQUEST_ERRORS_TOTAL = Counter(
    "bioetl_http_request_errors_total",
    "Total HTTP request errors",
    ["provider", "method", "error_type"],
)

PROVIDER_HEALTH_STATUS = Gauge(
    "bioetl_provider_health_status",
    "Provider health status (0=unknown, 1=healthy, 2=degraded)",
    ["provider"],
)

RATE_LIMITER_TOKENS_AVAILABLE = Gauge(
    "bioetl_rate_limiter_tokens_available",
    "Current tokens available in rate limiter",
    ["provider"],
)

RATE_LIMITER_WAIT_SECONDS = Histogram(
    "bioetl_rate_limiter_wait_seconds",
    "Rate limiter wait time in seconds",
    ["provider"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# =============================================================================
# Bronze / Silver storage metrics
# =============================================================================

BRONZE_WRITE_DURATION_SECONDS = Histogram(
    "bioetl_bronze_write_duration_seconds",
    "Duration of bronze write operations in seconds",
    ["provider", "entity"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
)

BRONZE_RECORDS_WRITTEN_TOTAL = Counter(
    "bioetl_bronze_records_written_total",
    "Total records written to bronze layer",
    ["provider", "entity"],
)

BRONZE_BYTES_WRITTEN_TOTAL = Counter(
    "bioetl_bronze_bytes_written_total",
    "Total bytes written to bronze layer (compressed)",
    ["provider", "entity"],
)

POLICY_VIOLATIONS_TOTAL = Counter(
    "bioetl_policy_violations_total",
    "Total write policy violations",
    ["layer", "mode"],
)

SILVER_VALIDATION_FAILURES_TOTAL = Counter(
    "bioetl_silver_validation_failures_total",
    "Total silver schema validation failures",
    ["table"],
)
