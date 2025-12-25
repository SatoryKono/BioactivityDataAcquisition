"""Prometheus Metrics for BioETL."""

from __future__ import annotations

from typing import Any

from prometheus_client import Counter, Gauge, Histogram

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

# Circuit Breaker metrics (per ADR-007)
CIRCUIT_BREAKER_STATE = Gauge(
    "bioetl_circuit_breaker_state",
    "Current state of the circuit breaker (0=closed, 0.5=half-open, 1=open)",
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
