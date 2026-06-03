"""Adapter, HTTP, and provider health metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

__all__ = [
    "ADAPTER_BATCH_SIZE",
    "ADAPTER_DROPPED_DUPLICATES_TOTAL",
    "ADAPTER_ERROR_TAXONOMY_TOTAL",
    "ADAPTER_FALLBACK_ATTEMPTS_TOTAL",
    "ADAPTER_FALLBACK_HITS_TOTAL",
    "ADAPTER_FALLBACK_HIT_RATE",
    "ADAPTER_REQUESTS_TOTAL",
    "ADAPTER_REQUEST_DURATION_SECONDS",
    "ADAPTER_REQUEST_P95_SECONDS",
    "DATA_SOURCE_RETRIES_TOTAL",
    "DATA_SOURCE_RETRY_EXHAUSTED_TOTAL",
    "HTTP_REQUEST_DURATION_SECONDS",
    "HTTP_REQUEST_ERRORS_TOTAL",
    "HTTP_RETRIES_TOTAL",
    "HTTP_RETRY_BUDGET_EXHAUSTED_TOTAL",
    "PROVIDER_HEALTH_STATUS",
    "RATE_LIMITER_TOKENS_AVAILABLE",
    "RATE_LIMITER_WAIT_SECONDS",
]

ADAPTER_REQUEST_DURATION_SECONDS = Histogram(
    "bioetl_adapter_request_duration_seconds",
    "Duration of adapter API requests in seconds",
    ["provider", "endpoint"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

# Compatibility alias for older import paths that still expect the removed
# rolling p95 symbol. Keep the canonical runtime metric surface on the
# histogram-backed duration metric while avoiding import-time breakage.
ADAPTER_REQUEST_P95_SECONDS = ADAPTER_REQUEST_DURATION_SECONDS

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

HTTP_RETRY_BUDGET_EXHAUSTED_TOTAL = Counter(
    "bioetl_http_retry_budget_exhausted_total",
    "Total HTTP requests that exhausted their retry budget",
    ["provider", "method"],
)

HTTP_REQUEST_ERRORS_TOTAL = Counter(
    "bioetl_http_request_errors_total",
    "Total HTTP request errors",
    ["provider", "method", "error_type"],
)

PROVIDER_HEALTH_STATUS = Gauge(
    "bioetl_provider_health_status",
    "Provider health status (0=unhealthy, 1=degraded, 2=healthy)",
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
