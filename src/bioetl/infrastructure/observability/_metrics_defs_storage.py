"""Bronze/Silver storage write-path metrics."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

__all__ = [
    "BRONZE_BYTES_WRITTEN_TOTAL",
    "BRONZE_RECORDS_WRITTEN_TOTAL",
    "BRONZE_WRITE_DURATION_SECONDS",
    "POLICY_VIOLATIONS_TOTAL",
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
