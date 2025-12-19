"""Prometheus Metrics for BioETL."""

from prometheus_client import Counter, Histogram

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
