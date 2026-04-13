"""Bronze/Silver storage write-path metrics."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

__all__ = [
    "BRONZE_BYTES_FREED_TOTAL",
    "BRONZE_BYTES_WRITTEN_TOTAL",
    "BRONZE_FILES_REMOVED_TOTAL",
    "BRONZE_RECORDS_WRITTEN_TOTAL",
    "BRONZE_WRITE_ATTEMPTS_TOTAL",
    "BRONZE_WRITE_DURATION_SECONDS",
    "BRONZE_WRITE_TOTAL_DURATION_SECONDS",
    "METADATA_WRITE_OUTCOMES_TOTAL",
    "METADATA_WRITE_RETRIES_TOTAL",
    "POLICY_VIOLATIONS_TOTAL",
    "SILVER_MERGE_FAILURES_TOTAL",
    "SILVER_MERGE_RETRIES_TOTAL",
    "SILVER_VALIDATION_FAILURES_TOTAL",
]

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
