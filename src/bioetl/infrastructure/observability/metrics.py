"""Prometheus Metrics for BioETL."""

from typing import Any

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


class MetricsCollector:
    """Collector for pipeline metrics.

    Wraps Prometheus metrics with pipeline context.
    """

    def __init__(self, pipeline_name: str, registry: Any = None):
        """Initialize the metrics collector.

        Args:
            pipeline_name: Name of the pipeline.
            registry: Optional Prometheus registry (unused as metrics are global).

        """
        self.pipeline_name = pipeline_name
        self.registry = registry

    def record_processed(
        self,
        layer: str,
        count: int = 1,
        run_type: str = "incremental",
    ) -> None:
        """Record processed records count.

        Args:
            layer: Processing layer (bronze, silver, gold).
            count: Number of records processed.
            run_type: Type of run (incremental, backfill).

        """
        RECORDS_PROCESSED_TOTAL.labels(
            pipeline=self.pipeline_name,
            stage=layer,
            run_type=run_type,
        ).inc(count)

    def record_error(self, error_code: str, stage: str = "processing") -> None:
        """Record an error.

        Args:
            error_code: Error code identifier.
            stage: Stage where error occurred.

        """
        ERRORS_TOTAL.labels(
            pipeline=self.pipeline_name,
            stage=stage,
            error_code=error_code,
        ).inc()
