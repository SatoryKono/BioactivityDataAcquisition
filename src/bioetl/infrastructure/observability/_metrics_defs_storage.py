"""Bronze/Silver storage write-path metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

__all__ = [
    "AUDIT_QUERY_DURATION_SECONDS",
    "AUDIT_QUERY_EVENTS_TOTAL",
    "AUDIT_WRITE_DURATION_SECONDS",
    "AUDIT_WRITE_EVENTS_TOTAL",
    "BRONZE_BYTES_FREED_TOTAL",
    "BRONZE_BYTES_WRITTEN_TOTAL",
    "BRONZE_FILES_REMOVED_TOTAL",
    "BRONZE_RECORDS_WRITTEN_TOTAL",
    "BRONZE_WRITE_ATTEMPTS_TOTAL",
    "BRONZE_WRITE_DURATION_SECONDS",
    "BRONZE_WRITE_TOTAL_DURATION_SECONDS",
    "GOLD_LIFECYCLE_STATE_TOTAL",
    "GOLD_VALIDATION_FAILURES_TOTAL",
    "GOLD_WRITE_ATTEMPTS_TOTAL",
    "GOLD_WRITE_DURATION_SECONDS",
    "GOLD_WRITE_OUTCOMES_TOTAL",
    "METADATA_WRITE_OUTCOMES_TOTAL",
    "METADATA_WRITE_RETRIES_TOTAL",
    "POLICY_VIOLATIONS_TOTAL",
    "SILVER_CSV_EXPORT_FAILURES_TOTAL",
    "SILVER_CSV_EXPORT_START_TOTAL",
    "SILVER_CSV_EXPORT_SUCCESS_TOTAL",
    "SILVER_MERGE_FAILURES_TOTAL",
    "SILVER_MERGE_RETRIES_TOTAL",
    "SILVER_OPTIMIZE_START_TOTAL",
    "SILVER_OPTIMIZE_SUCCESS_TOTAL",
    "SILVER_VACUUM_FILES_REMOVED",
    "SILVER_VACUUM_START_TOTAL",
    "SILVER_VACUUM_SUCCESS_TOTAL",
    "SILVER_VALIDATION_FAILURES_TOTAL",
]

AUDIT_WRITE_EVENTS_TOTAL = Counter(
    "bioetl_audit_write_events_total",
    "Total audit log write outcomes",
    ["layer", "operation", "status"],
)

AUDIT_WRITE_DURATION_SECONDS = Histogram(
    "bioetl_audit_write_duration_seconds",
    "Duration of audit log write operations in seconds",
    ["layer", "operation", "status"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

AUDIT_QUERY_EVENTS_TOTAL = Counter(
    "bioetl_audit_query_events_total",
    "Total audit query outcomes",
    ["layer_filter", "status"],
)

AUDIT_QUERY_DURATION_SECONDS = Histogram(
    "bioetl_audit_query_duration_seconds",
    "Duration of audit query operations in seconds",
    ["layer_filter", "status"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

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

BRONZE_WRITE_ATTEMPTS_TOTAL = Counter(
    "bioetl_bronze_write_attempts_total",
    "Total Bronze write attempts",
    ["provider", "entity"],
)

BRONZE_BYTES_WRITTEN_TOTAL = Counter(
    "bioetl_bronze_bytes_written_total",
    "Total bytes written to bronze layer (compressed)",
    ["provider", "entity"],
)

BRONZE_FILES_REMOVED_TOTAL = Counter(
    "bioetl_bronze_files_removed_total",
    "Total Bronze files removed by cleanup maintenance",
    ["operation"],
)

BRONZE_BYTES_FREED_TOTAL = Counter(
    "bioetl_bronze_bytes_freed_total",
    "Total Bronze bytes freed by cleanup maintenance",
    ["operation"],
)

BRONZE_WRITE_TOTAL_DURATION_SECONDS = Histogram(
    "bioetl_bronze_write_total_duration_seconds",
    "Total Bronze write duration, including side effects and metadata writes",
    ["provider", "entity"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
)

POLICY_VIOLATIONS_TOTAL = Counter(
    "bioetl_policy_violations_total",
    "Total write policy violations",
    ["layer", "mode"],
)

SILVER_MERGE_RETRIES_TOTAL = Counter(
    "bioetl_silver_merge_retries_total",
    "Total Silver merge retry attempts emitted by storage resilience helpers",
    ["pipeline", "retry_type"],
)

SILVER_MERGE_FAILURES_TOTAL = Counter(
    "bioetl_silver_merge_failures_total",
    "Total exhausted Silver merge failures emitted by storage resilience helpers",
    ["pipeline", "final_reason"],
)

SILVER_VALIDATION_FAILURES_TOTAL = Counter(
    "bioetl_silver_validation_failures_total",
    "Total silver schema validation failures",
    ["table", "pipeline"],
)

GOLD_WRITE_ATTEMPTS_TOTAL = Counter(
    "bioetl_gold_write_attempts_total",
    "Total Gold write attempts entering the storage write pipeline",
    ["pipeline", "table", "mode"],
)

GOLD_WRITE_OUTCOMES_TOTAL = Counter(
    "bioetl_gold_write_outcomes_total",
    "Total Gold write terminal outcomes emitted by the storage write pipeline",
    ["pipeline", "table", "mode", "status"],
)

GOLD_WRITE_DURATION_SECONDS = Histogram(
    "bioetl_gold_write_duration_seconds",
    "Duration of Gold write operations in seconds",
    ["pipeline", "table", "mode", "status"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0],
)

GOLD_VALIDATION_FAILURES_TOTAL = Counter(
    "bioetl_gold_validation_failures_total",
    "Total Gold write validation failures before physical storage dispatch",
    ["pipeline", "table", "mode", "error_type"],
)

GOLD_LIFECYCLE_STATE_TOTAL = Counter(
    "bioetl_gold_lifecycle_state_total",
    "Total application-owned Gold lifecycle state decisions",
    ["pipeline", "table", "state"],
)

METADATA_WRITE_RETRIES_TOTAL = Counter(
    "bioetl_metadata_write_retries_total",
    "Total metadata sidecar atomic-write retry attempts",
    ["layer", "provider", "pipeline", "reason"],
)

METADATA_WRITE_OUTCOMES_TOTAL = Counter(
    "bioetl_metadata_write_outcomes_total",
    "Total metadata sidecar write outcomes",
    ["layer", "provider", "pipeline", "status", "final_reason"],
)

SILVER_CSV_EXPORT_START_TOTAL = Counter(
    "bioetl_silver_csv_export_start_total",
    "Total Silver CSV export operations started",
    ["table", "pipeline"],
)

SILVER_CSV_EXPORT_SUCCESS_TOTAL = Counter(
    "bioetl_silver_csv_export_success_total",
    "Total successful Silver CSV export operations",
    ["table", "pipeline"],
)

SILVER_CSV_EXPORT_FAILURES_TOTAL = Counter(
    "bioetl_silver_csv_export_failures_total",
    "Total failed Silver CSV export operations",
    ["table", "pipeline", "error_type"],
)

SILVER_VACUUM_START_TOTAL = Counter(
    "bioetl_silver_vacuum_start_total",
    "Total Silver vacuum operations started",
)

SILVER_VACUUM_SUCCESS_TOTAL = Counter(
    "bioetl_silver_vacuum_success_total",
    "Total successful Silver vacuum operations",
)

SILVER_VACUUM_FILES_REMOVED = Gauge(
    "bioetl_silver_vacuum_files_removed",
    "Current number of files removed by the latest Silver vacuum operation",
)

SILVER_OPTIMIZE_START_TOTAL = Counter(
    "bioetl_silver_optimize_start_total",
    "Total Silver optimize operations started",
)

SILVER_OPTIMIZE_SUCCESS_TOTAL = Counter(
    "bioetl_silver_optimize_success_total",
    "Total successful Silver optimize operations",
)
