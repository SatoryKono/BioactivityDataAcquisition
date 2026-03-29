"""Grouped Prometheus metric registries and machine-readable inventory."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from prometheus_client.metrics import Counter, Gauge, Histogram

from bioetl.infrastructure.observability.metrics import (
    ADAPTER_BATCH_SIZE,
    ADAPTER_DROPPED_DUPLICATES_TOTAL,
    ADAPTER_ERROR_TAXONOMY_TOTAL,
    ADAPTER_FALLBACK_ATTEMPTS_TOTAL,
    ADAPTER_FALLBACK_HIT_RATE,
    ADAPTER_FALLBACK_HITS_TOTAL,
    ADAPTER_REQUEST_DURATION_SECONDS,
    ADAPTER_REQUEST_P95_SECONDS,
    ADAPTER_REQUESTS_TOTAL,
    ARCHIVE_DURATION_SECONDS,
    ARCHIVE_FILES_TOTAL,
    BATCH_SIZE_RECORDS,
    BRONZE_BYTES_WRITTEN_TOTAL,
    BRONZE_RECORDS_WRITTEN_TOTAL,
    BRONZE_WRITE_DURATION_SECONDS,
    CHECKPOINT_COMPATIBILITY_EVENTS_TOTAL,
    CIRCUIT_BREAKER_FAILURE_TOTAL,
    CIRCUIT_BREAKER_STATE,
    CIRCUIT_BREAKER_SUCCESS_TOTAL,
    CIRCUIT_BREAKER_TRIPS_TOTAL,
    COMPOSITE_SOURCE_SELECTION_TOTAL,
    CONTROL_PLANE_READ_DURATION_SECONDS,
    CONTROL_PLANE_READS_TOTAL,
    CONTROL_PLANE_LEDGER_APPENDS_TOTAL,
    CONTROL_PLANE_MANIFEST_WRITES_TOTAL,
    DATA_FRESHNESS_SECONDS,
    DATA_SOURCE_RETRIES_TOTAL,
    DATA_SOURCE_RETRY_EXHAUSTED_TOTAL,
    DQ_CONTEXT_BUILD_FAILURES_TOTAL,
    DQ_ANOMALY_DETECTED,
    DQ_BASELINE_SAMPLES,
    DQ_BASELINE_UPDATED,
    DQ_CHECK_DURATION_MS,
    DQ_RECORDS_QUARANTINED_TOTAL,
    DQ_REPORT_GENERATED_TOTAL,
    DQ_REPORT_SKIPPED_TOTAL,
    DQ_SOFT_THRESHOLD_EXCEEDED,
    DQ_VALIDATION_FAILURES_TOTAL,
    DQ_VALIDATION_SCORE,
    ERRORS_TOTAL,
    FILTER_COMBINATIONS_LOADED_TOTAL,
    FILTER_IDS_DUPLICATES_TOTAL,
    FILTER_IDS_LOADED_TOTAL,
    HEALTH_CHECK_DURATION_SECONDS,
    HEALTH_CHECK_DEGRADED_TOTAL,
    HEALTH_CHECK_FAILURES_TOTAL,
    HEALTH_CHECK_LATENCY_MS,
    HEALTH_CHECK_LATENCY_SECONDS,
    HEALTH_CHECK_MODE_LATENCY_MS,
    HEALTH_CHECK_MODE_STATUS,
    HEALTH_CHECK_STATUS,
    HEALTH_CHECK_SUCCESS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUEST_ERRORS_TOTAL,
    HTTP_RETRIES_TOTAL,
    INFRASTRUCTURE_VALIDATED,
    LINEAGE_FRAGMENTS_EMITTED_TOTAL,
    LINEAGE_REFS_MISSING_TOTAL,
    OBSERVABILITY_EVENTS_TOTAL,
    PHASE_DURATION_SECONDS,
    PIPELINE_DURATION_SECONDS,
    PIPELINE_HEALTH_CHECK_PASSED,
    PIPELINE_RUNS_TOTAL,
    POLICY_VIOLATIONS_TOTAL,
    PREFLIGHT_CONFIG_ERRORS_TOTAL,
    PREFLIGHT_MEDALLION_POLICY_VALID,
    PROBE_MODE_FALLBACK_TOTAL,
    PROVIDER_HEALTH_STATUS,
    QUARANTINE_RECORDS_TOTAL,
    RATE_LIMITER_TOKENS_AVAILABLE,
    RATE_LIMITER_WAIT_SECONDS,
    RECORDS_PROCESSED_TOTAL,
    SHUTDOWN_COMPLETED,
    SHUTDOWN_INITIATED,
    SILVER_VALIDATION_FAILURES_TOTAL,
    STORAGE_OPTIMIZATION_TOTAL,
    TRACED_RUNS_TOTAL,
    TRANSFORM_DURATION_SECONDS,
    TRANSFORM_ERRORS_TOTAL,
    VACUUM_DURATION_SECONDS,
    VACUUM_FILES_REMOVED_TOTAL,
)

PrometheusCounter = Counter
PrometheusGauge = Gauge
PrometheusHistogram = Histogram


@dataclass(frozen=True, slots=True)
class MetricRegistryFamily:
    """Logical family of public Prometheus metric registries."""

    family: str
    counters: Mapping[str, PrometheusCounter]
    gauges: Mapping[str, PrometheusGauge]
    histograms: Mapping[str, PrometheusHistogram]


PIPELINE_RUNTIME_REGISTRY = MetricRegistryFamily(
    family="pipeline_runtime",
    counters={
        "records_processed_total": RECORDS_PROCESSED_TOTAL,
        "errors_total": ERRORS_TOTAL,
        "filter_ids_loaded_total": FILTER_IDS_LOADED_TOTAL,
        "filter_ids_duplicates_total": FILTER_IDS_DUPLICATES_TOTAL,
        "bioetl_pipeline_runs_total": PIPELINE_RUNS_TOTAL,
        "shutdown_initiated": SHUTDOWN_INITIATED,
        "shutdown_completed": SHUTDOWN_COMPLETED,
        "filter_combinations_loaded_total": FILTER_COMBINATIONS_LOADED_TOTAL,
        "transform_errors_total": TRANSFORM_ERRORS_TOTAL,
        "control_plane_manifest_writes_total": CONTROL_PLANE_MANIFEST_WRITES_TOTAL,
        "control_plane_ledger_appends_total": CONTROL_PLANE_LEDGER_APPENDS_TOTAL,
        "control_plane_reads_total": CONTROL_PLANE_READS_TOTAL,
        "checkpoint_compatibility_events_total": CHECKPOINT_COMPATIBILITY_EVENTS_TOTAL,
        "traced_runs_total": TRACED_RUNS_TOTAL,
    },
    gauges={},
    histograms={
        "pipeline_duration_seconds": PIPELINE_DURATION_SECONDS,
        "batch_size_records": BATCH_SIZE_RECORDS,
        "bioetl_phase_duration_seconds": PHASE_DURATION_SECONDS,
        "transform_duration_seconds": TRANSFORM_DURATION_SECONDS,
        "control_plane_read_duration_seconds": CONTROL_PLANE_READ_DURATION_SECONDS,
    },
)

STORAGE_MEDALLION_REGISTRY = MetricRegistryFamily(
    family="storage_medallion",
    counters={
        "vacuum_files_removed_total": VACUUM_FILES_REMOVED_TOTAL,
        "archive_files_total": ARCHIVE_FILES_TOTAL,
        "storage_optimization_total": STORAGE_OPTIMIZATION_TOTAL,
        "bronze_records_written_total": BRONZE_RECORDS_WRITTEN_TOTAL,
        "bronze_bytes_written_total": BRONZE_BYTES_WRITTEN_TOTAL,
        "policy_violations_total": POLICY_VIOLATIONS_TOTAL,
        "silver_validation_failures_total": SILVER_VALIDATION_FAILURES_TOTAL,
        "quarantine_records_total": QUARANTINE_RECORDS_TOTAL,
        "lineage_fragments_emitted_total": LINEAGE_FRAGMENTS_EMITTED_TOTAL,
        "lineage_refs_missing_total": LINEAGE_REFS_MISSING_TOTAL,
        "composite_source_selection_total": COMPOSITE_SOURCE_SELECTION_TOTAL,
    },
    gauges={},
    histograms={
        "vacuum_duration_seconds": VACUUM_DURATION_SECONDS,
        "archive_duration_seconds": ARCHIVE_DURATION_SECONDS,
        "bronze_write_duration_seconds": BRONZE_WRITE_DURATION_SECONDS,
    },
)

HTTP_ADAPTER_REGISTRY = MetricRegistryFamily(
    family="http_adapters",
    counters={
        "adapter_requests_total": ADAPTER_REQUESTS_TOTAL,
        "adapter_dropped_duplicates_total": ADAPTER_DROPPED_DUPLICATES_TOTAL,
        "adapter_fallback_attempts_total": ADAPTER_FALLBACK_ATTEMPTS_TOTAL,
        "adapter_fallback_hits_total": ADAPTER_FALLBACK_HITS_TOTAL,
        "adapter_error_taxonomy_total": ADAPTER_ERROR_TAXONOMY_TOTAL,
        "data_source_retries_total": DATA_SOURCE_RETRIES_TOTAL,
        "data_source_retry_exhausted_total": DATA_SOURCE_RETRY_EXHAUSTED_TOTAL,
        "http_retries_total": HTTP_RETRIES_TOTAL,
        "http_request_errors_total": HTTP_REQUEST_ERRORS_TOTAL,
    },
    gauges={
        "provider_health_status": PROVIDER_HEALTH_STATUS,
        "adapter_request_p95_seconds": ADAPTER_REQUEST_P95_SECONDS,
        "adapter_fallback_hit_rate": ADAPTER_FALLBACK_HIT_RATE,
        "bioetl_rate_limiter_tokens_available": RATE_LIMITER_TOKENS_AVAILABLE,
    },
    histograms={
        "adapter_request_duration_seconds": ADAPTER_REQUEST_DURATION_SECONDS,
        "adapter_batch_size": ADAPTER_BATCH_SIZE,
        "http_request_duration_seconds": HTTP_REQUEST_DURATION_SECONDS,
        "bioetl_rate_limiter_wait_seconds": RATE_LIMITER_WAIT_SECONDS,
    },
)

DQ_VALIDATION_REGISTRY = MetricRegistryFamily(
    family="dq_validation",
    counters={
        "dq_context_build_failures_total": DQ_CONTEXT_BUILD_FAILURES_TOTAL,
        "dq_records_quarantined_total": DQ_RECORDS_QUARANTINED_TOTAL,
        "dq_anomaly_detected": DQ_ANOMALY_DETECTED,
        "dq_baseline_updated": DQ_BASELINE_UPDATED,
        "dq_report_generated_total": DQ_REPORT_GENERATED_TOTAL,
        "dq_report_skipped_total": DQ_REPORT_SKIPPED_TOTAL,
        "dq_soft_threshold_exceeded": DQ_SOFT_THRESHOLD_EXCEEDED,
        "dq_validation_failures_total": DQ_VALIDATION_FAILURES_TOTAL,
        "observability_events_total": OBSERVABILITY_EVENTS_TOTAL,
    },
    gauges={
        "dq_baseline_samples": DQ_BASELINE_SAMPLES,
        "dq_validation_score": DQ_VALIDATION_SCORE,
        "data_freshness_seconds": DATA_FRESHNESS_SECONDS,
    },
    histograms={
        "dq_check_duration_ms": DQ_CHECK_DURATION_MS,
    },
)

SYSTEM_PROCESS_REGISTRY = MetricRegistryFamily(
    family="system_process",
    counters={
        "circuit_breaker_trips_total": CIRCUIT_BREAKER_TRIPS_TOTAL,
        "circuit_breaker_success_total": CIRCUIT_BREAKER_SUCCESS_TOTAL,
        "circuit_breaker_failure_total": CIRCUIT_BREAKER_FAILURE_TOTAL,
        "health_check_degraded_total": HEALTH_CHECK_DEGRADED_TOTAL,
        "health_check_success_total": HEALTH_CHECK_SUCCESS_TOTAL,
        "health_check_failures_total": HEALTH_CHECK_FAILURES_TOTAL,
        "probe_mode_fallback_total": PROBE_MODE_FALLBACK_TOTAL,
    },
    gauges={
        "circuit_breaker_state": CIRCUIT_BREAKER_STATE,
        "pipeline_health_check_passed": PIPELINE_HEALTH_CHECK_PASSED,
        "infrastructure_validated": INFRASTRUCTURE_VALIDATED,
        "health_check_status": HEALTH_CHECK_STATUS,
        "health_check_mode_status": HEALTH_CHECK_MODE_STATUS,
        "preflight_medallion_policy_valid": PREFLIGHT_MEDALLION_POLICY_VALID,
        "preflight_config_errors_total": PREFLIGHT_CONFIG_ERRORS_TOTAL,
    },
    histograms={
        "health_check_duration_seconds": HEALTH_CHECK_DURATION_SECONDS,
        "health_check_latency_ms": HEALTH_CHECK_LATENCY_MS,
        "health_check_mode_latency_ms": HEALTH_CHECK_MODE_LATENCY_MS,
        "health_check_latency_seconds": HEALTH_CHECK_LATENCY_SECONDS,
    },
)

METRIC_REGISTRY_FAMILIES: tuple[MetricRegistryFamily, ...] = (
    PIPELINE_RUNTIME_REGISTRY,
    STORAGE_MEDALLION_REGISTRY,
    HTTP_ADAPTER_REGISTRY,
    DQ_VALIDATION_REGISTRY,
    SYSTEM_PROCESS_REGISTRY,
)

METRIC_REGISTRY_INVENTORY: dict[str, dict[str, tuple[str, ...]]] = {
    family.family: {
        "counters": tuple(family.counters.keys()),
        "gauges": tuple(family.gauges.keys()),
        "histograms": tuple(family.histograms.keys()),
    }
    for family in METRIC_REGISTRY_FAMILIES
}


def build_counter_registry() -> dict[str, PrometheusCounter]:
    """Merge grouped counter registries into one public mapping."""
    merged: dict[str, PrometheusCounter] = {}
    for family in METRIC_REGISTRY_FAMILIES:
        merged.update(family.counters)
    return merged


def build_gauge_registry() -> dict[str, PrometheusGauge]:
    """Merge grouped gauge registries into one public mapping."""
    merged: dict[str, PrometheusGauge] = {}
    for family in METRIC_REGISTRY_FAMILIES:
        merged.update(family.gauges)
    return merged


def build_histogram_registry() -> dict[str, PrometheusHistogram]:
    """Merge grouped histogram registries into one public mapping."""
    merged: dict[str, PrometheusHistogram] = {}
    for family in METRIC_REGISTRY_FAMILIES:
        merged.update(family.histograms)
    return merged


COUNTERS = build_counter_registry()
GAUGES = build_gauge_registry()
HISTOGRAMS = build_histogram_registry()

REGISTERED_PROMETHEUS_METRIC_NAMES = frozenset(
    set(COUNTERS) | set(GAUGES) | set(HISTOGRAMS)
)

__all__ = [
    "COUNTERS",
    "DQ_VALIDATION_REGISTRY",
    "GAUGES",
    "HISTOGRAMS",
    "HTTP_ADAPTER_REGISTRY",
    "METRIC_REGISTRY_FAMILIES",
    "METRIC_REGISTRY_INVENTORY",
    "PIPELINE_RUNTIME_REGISTRY",
    "REGISTERED_PROMETHEUS_METRIC_NAMES",
    "STORAGE_MEDALLION_REGISTRY",
    "SYSTEM_PROCESS_REGISTRY",
    "MetricRegistryFamily",
    "build_counter_registry",
    "build_gauge_registry",
    "build_histogram_registry",
]
