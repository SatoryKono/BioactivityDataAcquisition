"""Prometheus Metrics adapter implementing MetricsPort.

Provides concrete implementation of the MetricsPort interface using
Prometheus client library.
"""

from __future__ import annotations

from bioetl.domain.ports import MetricsPort
from bioetl.infrastructure.observability.metrics import (
    ADAPTER_BATCH_SIZE,
    ADAPTER_DROPPED_DUPLICATES_TOTAL,
    ADAPTER_REQUEST_DURATION_SECONDS,
    ADAPTER_REQUESTS_TOTAL,
    ARCHIVE_DURATION_SECONDS,
    ARCHIVE_FILES_TOTAL,
    BATCH_SIZE_RECORDS,
    BRONZE_BYTES_WRITTEN_TOTAL,
    BRONZE_RECORDS_WRITTEN_TOTAL,
    BRONZE_WRITE_DURATION_SECONDS,
    CIRCUIT_BREAKER_FAILURE_TOTAL,
    CIRCUIT_BREAKER_STATE,
    CIRCUIT_BREAKER_SUCCESS_TOTAL,
    CIRCUIT_BREAKER_TRIPS_TOTAL,
    DATA_FRESHNESS_SECONDS,
    DATA_SOURCE_RETRIES_TOTAL,
    DATA_SOURCE_RETRY_EXHAUSTED_TOTAL,
    DQ_ANOMALY_DETECTED,
    DQ_BASELINE_SAMPLES,
    DQ_BASELINE_UPDATED,
    DQ_CHECK_DURATION_MS,
    DQ_RECORDS_QUARANTINED_TOTAL,
    DQ_SOFT_THRESHOLD_EXCEEDED,
    DQ_VALIDATION_FAILURES_TOTAL,
    DQ_VALIDATION_SCORE,
    ERRORS_TOTAL,
    FILTER_COMBINATIONS_LOADED_TOTAL,
    FILTER_IDS_DUPLICATES_TOTAL,
    FILTER_IDS_LOADED_TOTAL,
    HEALTH_CHECK_DURATION_SECONDS,
    HEALTH_CHECK_FAILURES_TOTAL,
    HEALTH_CHECK_LATENCY_MS,
    HEALTH_CHECK_LATENCY_SECONDS,
    HEALTH_CHECK_STATUS,
    HEALTH_CHECK_SUCCESS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUEST_ERRORS_TOTAL,
    HTTP_RETRIES_TOTAL,
    INFRASTRUCTURE_VALIDATED,
    PHASE_DURATION_SECONDS,
    PIPELINE_DURATION_SECONDS,
    PIPELINE_HEALTH_CHECK_PASSED,
    PIPELINE_RUNS_TOTAL,
    POLICY_VIOLATIONS_TOTAL,
    PREFLIGHT_CONFIG_ERRORS_TOTAL,
    PREFLIGHT_MEDALLION_POLICY_VALID,
    PROVIDER_HEALTH_STATUS,
    QUARANTINE_RECORDS_TOTAL,
    RATE_LIMITER_TOKENS_AVAILABLE,
    RATE_LIMITER_WAIT_SECONDS,
    RECORDS_PROCESSED_TOTAL,
    SHUTDOWN_COMPLETED,
    SHUTDOWN_INITIATED,
    SILVER_VALIDATION_FAILURES_TOTAL,
    STORAGE_OPTIMIZATION_TOTAL,
    TRANSFORM_DURATION_SECONDS,
    TRANSFORM_ERRORS_TOTAL,
    VACUUM_DURATION_SECONDS,
    VACUUM_FILES_REMOVED_TOTAL,
)

_ALLOWED_REASON_LABELS = frozenset(
    {
        "cross_validation",
        "filtered_out_silver",
        "data_quality",
        "schema_validation",
        "transform_error",
        "validation_error",
        "other",
    }
)
_ALLOWED_STAGE_LABELS = frozenset(
    {
        "validation",
        "threshold",
        "transform",
        "silver",
        "gold",
        "postrun",
        "other",
    }
)
_ALLOWED_SEVERITY_LABELS = frozenset(
    {"soft_fail", "hard_fail", "warning", "error", "other"}
)


def _normalize_label(value: str, allowed_values: frozenset[str]) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized if normalized in allowed_values else "other"


# Registry of histogram metrics
HISTOGRAMS = {
    "pipeline_duration_seconds": PIPELINE_DURATION_SECONDS,
    "batch_size_records": BATCH_SIZE_RECORDS,
    "vacuum_duration_seconds": VACUUM_DURATION_SECONDS,
    "archive_duration_seconds": ARCHIVE_DURATION_SECONDS,
    "dq_check_duration_ms": DQ_CHECK_DURATION_MS,
    "bioetl_phase_duration_seconds": PHASE_DURATION_SECONDS,
    "health_check_duration_seconds": HEALTH_CHECK_DURATION_SECONDS,
    "health_check_latency_ms": HEALTH_CHECK_LATENCY_MS,
    "health_check_latency_seconds": HEALTH_CHECK_LATENCY_SECONDS,
    "transform_duration_seconds": TRANSFORM_DURATION_SECONDS,
    "adapter_request_duration_seconds": ADAPTER_REQUEST_DURATION_SECONDS,
    "adapter_batch_size": ADAPTER_BATCH_SIZE,
    "http_request_duration_seconds": HTTP_REQUEST_DURATION_SECONDS,
    "bioetl_rate_limiter_wait_seconds": RATE_LIMITER_WAIT_SECONDS,
    "bronze_write_duration_seconds": BRONZE_WRITE_DURATION_SECONDS,
}

# Registry of counter metrics
COUNTERS = {
    "records_processed_total": RECORDS_PROCESSED_TOTAL,
    "errors_total": ERRORS_TOTAL,
    "filter_ids_loaded_total": FILTER_IDS_LOADED_TOTAL,
    "filter_ids_duplicates_total": FILTER_IDS_DUPLICATES_TOTAL,
    "dq_records_quarantined_total": DQ_RECORDS_QUARANTINED_TOTAL,
    "circuit_breaker_trips_total": CIRCUIT_BREAKER_TRIPS_TOTAL,
    "circuit_breaker_success_total": CIRCUIT_BREAKER_SUCCESS_TOTAL,
    "circuit_breaker_failure_total": CIRCUIT_BREAKER_FAILURE_TOTAL,
    "vacuum_files_removed_total": VACUUM_FILES_REMOVED_TOTAL,
    "archive_files_total": ARCHIVE_FILES_TOTAL,
    "dq_anomaly_detected": DQ_ANOMALY_DETECTED,
    "dq_baseline_updated": DQ_BASELINE_UPDATED,
    "bioetl_pipeline_runs_total": PIPELINE_RUNS_TOTAL,
    "dq_soft_threshold_exceeded": DQ_SOFT_THRESHOLD_EXCEEDED,
    "shutdown_initiated": SHUTDOWN_INITIATED,
    "shutdown_completed": SHUTDOWN_COMPLETED,
    "storage_optimization_total": STORAGE_OPTIMIZATION_TOTAL,
    "filter_combinations_loaded_total": FILTER_COMBINATIONS_LOADED_TOTAL,
    "transform_errors_total": TRANSFORM_ERRORS_TOTAL,
    "adapter_requests_total": ADAPTER_REQUESTS_TOTAL,
    "adapter_dropped_duplicates_total": ADAPTER_DROPPED_DUPLICATES_TOTAL,
    "data_source_retries_total": DATA_SOURCE_RETRIES_TOTAL,
    "data_source_retry_exhausted_total": DATA_SOURCE_RETRY_EXHAUSTED_TOTAL,
    "health_check_success_total": HEALTH_CHECK_SUCCESS_TOTAL,
    "health_check_failures_total": HEALTH_CHECK_FAILURES_TOTAL,
    "http_retries_total": HTTP_RETRIES_TOTAL,
    "http_request_errors_total": HTTP_REQUEST_ERRORS_TOTAL,
    "bronze_records_written_total": BRONZE_RECORDS_WRITTEN_TOTAL,
    "bronze_bytes_written_total": BRONZE_BYTES_WRITTEN_TOTAL,
    "policy_violations_total": POLICY_VIOLATIONS_TOTAL,
    "silver_validation_failures_total": SILVER_VALIDATION_FAILURES_TOTAL,
    "quarantine_records_total": QUARANTINE_RECORDS_TOTAL,
    "dq_validation_failures_total": DQ_VALIDATION_FAILURES_TOTAL,
}

# Registry of gauge metrics
GAUGES = {
    "circuit_breaker_state": CIRCUIT_BREAKER_STATE,
    "dq_baseline_samples": DQ_BASELINE_SAMPLES,
    "dq_validation_score": DQ_VALIDATION_SCORE,
    "data_freshness_seconds": DATA_FRESHNESS_SECONDS,
    "pipeline_health_check_passed": PIPELINE_HEALTH_CHECK_PASSED,
    "infrastructure_validated": INFRASTRUCTURE_VALIDATED,
    "health_check_status": HEALTH_CHECK_STATUS,
    "preflight_medallion_policy_valid": PREFLIGHT_MEDALLION_POLICY_VALID,
    "preflight_config_errors_total": PREFLIGHT_CONFIG_ERRORS_TOTAL,
    "provider_health_status": PROVIDER_HEALTH_STATUS,
    "bioetl_rate_limiter_tokens_available": RATE_LIMITER_TOKENS_AVAILABLE,
}


class PrometheusMetrics(MetricsPort):
    """Prometheus implementation of MetricsPort.

    Uses the generic MetricsPort API with standardized metric names that map
    into ``HISTOGRAMS``, ``COUNTERS``, and ``GAUGES`` registries.

    Extension rule: add new metric definitions in
    ``infrastructure/observability/metrics.py`` and register them in this
    module, rather than creating duplicate domain-level metrics interfaces.
    """

    def __init__(self) -> None:
        self._closed = False

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str]
    ) -> None:
        """Record a histogram observation for the named metric.

        Args:
            name: Identifier name.
            value: Input value.
            labels: Labels.
        """
        if name in HISTOGRAMS:
            HISTOGRAMS[name].labels(**labels).observe(value)

    def increment_counter(self, name: str, value: int, labels: dict[str, str]) -> None:
        """Increment a counter metric by the given value.

        Args:
            name: Identifier name.
            value: Input value.
            labels: Labels.
        """
        if name in COUNTERS:
            COUNTERS[name].labels(**labels).inc(value)

    def set_gauge(self, name: str, value: float, labels: dict[str, str]) -> None:
        """Set a gauge metric to the given value.

        Args:
            name: Identifier name.
            value: Input value.
            labels: Labels.
        """
        if name in GAUGES:
            GAUGES[name].labels(**labels).set(value)

    def inc_quarantine_records(
        self, pipeline: str, reason: str, count: int = 1
    ) -> None:
        """Increment quarantine record counter with normalized reason label.

        Args:
            pipeline: Pipeline.
            reason: Reason description.
            count: Count.
        """
        bounded_reason = _normalize_label(reason, _ALLOWED_REASON_LABELS)
        self.increment_counter(
            "quarantine_records_total",
            count,
            {"pipeline": pipeline, "reason": bounded_reason},
        )

    def inc_dq_validation_failures(
        self,
        pipeline: str,
        stage: str,
        severity: str,
        count: int = 1,
    ) -> None:
        """Increment DQ validation failure counter with normalized labels.

        Args:
            pipeline: Pipeline.
            stage: Stage.
            severity: Severity.
            count: Count.
        """
        bounded_stage = _normalize_label(stage, _ALLOWED_STAGE_LABELS)
        bounded_severity = _normalize_label(severity, _ALLOWED_SEVERITY_LABELS)
        self.increment_counter(
            "dq_validation_failures_total",
            count,
            {
                "pipeline": pipeline,
                "stage": bounded_stage,
                "severity": bounded_severity,
            },
        )

    def close(self) -> None:
        """Mark the metrics adapter as closed (idempotent)."""
        if self._closed:
            return
        self._closed = True
