"""Prometheus Metrics adapter implementing MetricsPort.

Provides concrete implementation of the MetricsPort interface using
Prometheus client library.
"""

from __future__ import annotations

import logging

from bioetl.domain.ports import MetricsPort

_logger = logging.getLogger(__name__)
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

# Registry of histogram metrics
HISTOGRAMS = {
    "pipeline_duration_seconds": PIPELINE_DURATION_SECONDS,
    "batch_size_records": BATCH_SIZE_RECORDS,
    "vacuum_duration_seconds": VACUUM_DURATION_SECONDS,
    "archive_duration_seconds": ARCHIVE_DURATION_SECONDS,
    "dq_check_duration_ms": DQ_CHECK_DURATION_MS,
    # Pipeline lifecycle
    "phase_duration_seconds": PHASE_DURATION_SECONDS,
    "bioetl_phase_duration_seconds": PHASE_DURATION_SECONDS,  # alias for callers using full name
    # Health checks
    "health_check_duration_seconds": HEALTH_CHECK_DURATION_SECONDS,
    "health_check_latency_ms": HEALTH_CHECK_LATENCY_MS,
    "health_check_latency_seconds": HEALTH_CHECK_LATENCY_SECONDS,
    # Transformer
    "transform_duration_seconds": TRANSFORM_DURATION_SECONDS,
    # Adapter / HTTP
    "adapter_request_duration_seconds": ADAPTER_REQUEST_DURATION_SECONDS,
    "adapter_batch_size": ADAPTER_BATCH_SIZE,
    "http_request_duration_seconds": HTTP_REQUEST_DURATION_SECONDS,
    # Rate limiter
    "rate_limiter_wait_seconds": RATE_LIMITER_WAIT_SECONDS,
    "bioetl_rate_limiter_wait_seconds": RATE_LIMITER_WAIT_SECONDS,  # alias
    # Bronze storage
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
    # Pipeline lifecycle
    "pipeline_runs_total": PIPELINE_RUNS_TOTAL,
    "bioetl_pipeline_runs_total": PIPELINE_RUNS_TOTAL,  # alias
    # DQ
    "dq_soft_threshold_exceeded": DQ_SOFT_THRESHOLD_EXCEEDED,
    # Shutdown
    "shutdown_initiated": SHUTDOWN_INITIATED,
    "shutdown_completed": SHUTDOWN_COMPLETED,
    # Storage
    "storage_optimization_total": STORAGE_OPTIMIZATION_TOTAL,
    "filter_combinations_loaded_total": FILTER_COMBINATIONS_LOADED_TOTAL,
    # Transformer
    "transform_errors_total": TRANSFORM_ERRORS_TOTAL,
    # Adapter / HTTP
    "adapter_requests_total": ADAPTER_REQUESTS_TOTAL,
    "adapter_dropped_duplicates_total": ADAPTER_DROPPED_DUPLICATES_TOTAL,
    "data_source_retries_total": DATA_SOURCE_RETRIES_TOTAL,
    "data_source_retry_exhausted_total": DATA_SOURCE_RETRY_EXHAUSTED_TOTAL,
    "health_check_success_total": HEALTH_CHECK_SUCCESS_TOTAL,
    "health_check_failures_total": HEALTH_CHECK_FAILURES_TOTAL,
    "http_retries_total": HTTP_RETRIES_TOTAL,
    "http_request_errors_total": HTTP_REQUEST_ERRORS_TOTAL,
    # Bronze / Silver storage
    "bronze_records_written_total": BRONZE_RECORDS_WRITTEN_TOTAL,
    "bronze_bytes_written_total": BRONZE_BYTES_WRITTEN_TOTAL,
    "policy_violations_total": POLICY_VIOLATIONS_TOTAL,
    "silver_validation_failures_total": SILVER_VALIDATION_FAILURES_TOTAL,
}

# Registry of gauge metrics
GAUGES = {
    "circuit_breaker_state": CIRCUIT_BREAKER_STATE,
    "dq_baseline_samples": DQ_BASELINE_SAMPLES,
    "dq_validation_score": DQ_VALIDATION_SCORE,
    "data_freshness_seconds": DATA_FRESHNESS_SECONDS,
    # Health checks
    "pipeline_health_check_passed": PIPELINE_HEALTH_CHECK_PASSED,
    "infrastructure_validated": INFRASTRUCTURE_VALIDATED,
    "health_check_status": HEALTH_CHECK_STATUS,
    "preflight_medallion_policy_valid": PREFLIGHT_MEDALLION_POLICY_VALID,
    "preflight_config_errors_total": PREFLIGHT_CONFIG_ERRORS_TOTAL,
    # Provider health
    "provider_health_status": PROVIDER_HEALTH_STATUS,
    # Rate limiter
    "rate_limiter_tokens_available": RATE_LIMITER_TOKENS_AVAILABLE,
    "bioetl_rate_limiter_tokens_available": RATE_LIMITER_TOKENS_AVAILABLE,  # alias
}


class PrometheusMetrics(MetricsPort):
    """Prometheus implementation of MetricsPort.

    Maps metric names to pre-defined Prometheus metrics and records observations.
    """

    def __init__(self) -> None:
        """Initialize Prometheus metrics adapter."""
        self._closed = False

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        """Observe a value for a Prometheus histogram."""
        if name in HISTOGRAMS:
            HISTOGRAMS[name].labels(**labels).observe(value)
        else:
            _logger.warning("Unknown histogram metric: %s", name)

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str],
    ) -> None:
        """Increment a Prometheus counter."""
        if name in COUNTERS:
            COUNTERS[name].labels(**labels).inc(value)
        else:
            _logger.warning("Unknown counter metric: %s", name)

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        """Set a Prometheus gauge to a specific value."""
        if name in GAUGES:
            GAUGES[name].labels(**labels).set(value)
        else:
            _logger.warning("Unknown gauge metric: %s", name)

    def close(self) -> None:
        """Cleanup Prometheus metrics. Idempotent.

        Note: For the default global REGISTRY, this is a no-op since
        metrics are shared across the process. For custom registries,
        this could unregister collectors.
        """
        if self._closed:
            return
        # For default REGISTRY: no-op (shared across tests/process)
        # If using custom registry, could call registry.unregister() here
        self._closed = True


# NOTE: NoOpMetrics has been removed from this module to eliminate duplication.
# Use bioetl.infrastructure.observability.noop_metrics.NoOpMetrics instead.
