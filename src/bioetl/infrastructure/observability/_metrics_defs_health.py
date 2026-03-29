"""Health-check and preflight observability metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

__all__ = [
    "HEALTH_CHECK_DEGRADED_TOTAL",
    "HEALTH_CHECK_DURATION_SECONDS",
    "HEALTH_CHECK_FAILURES_TOTAL",
    "HEALTH_CHECK_LATENCY_MS",
    "HEALTH_CHECK_LATENCY_SECONDS",
    "HEALTH_CHECK_MODE_LATENCY_MS",
    "HEALTH_CHECK_MODE_STATUS",
    "HEALTH_CHECK_STATUS",
    "HEALTH_CHECK_SUCCESS_TOTAL",
    "INFRASTRUCTURE_VALIDATED",
    "PIPELINE_HEALTH_CHECK_PASSED",
    "PREFLIGHT_CONFIG_ERRORS_TOTAL",
    "PREFLIGHT_MEDALLION_POLICY_VALID",
    "PROBE_MODE_FALLBACK_TOTAL",
]

PIPELINE_HEALTH_CHECK_PASSED = Gauge(
    "bioetl_pipeline_health_check_passed",
    "Health check status for pipeline components (1=passed, 0=failed)",
    ["pipeline", "component"],
)

INFRASTRUCTURE_VALIDATED = Gauge(
    "bioetl_infrastructure_validated",
    "Infrastructure validation status (1=validated, 0=not validated)",
    ["pipeline"],
)

HEALTH_CHECK_DURATION_SECONDS = Histogram(
    "bioetl_health_check_duration_seconds",
    "Duration of health check operations in seconds",
    ["pipeline"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

HEALTH_CHECK_STATUS = Gauge(
    "bioetl_health_check_status",
    "Health check status per component (0=unknown, 1=healthy, 2=degraded)",
    ["component"],
)

HEALTH_CHECK_MODE_STATUS = Gauge(
    "bioetl_health_check_mode_status",
    "Health check status by mode and component (0=unknown, 1=healthy, 2=degraded)",
    ["component", "mode"],
)

HEALTH_CHECK_LATENCY_MS = Histogram(
    "bioetl_health_check_latency_ms",
    "Health check latency in milliseconds",
    ["provider"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000],
)

HEALTH_CHECK_MODE_LATENCY_MS = Histogram(
    "bioetl_health_check_mode_latency_ms",
    "Health check latency in milliseconds by health-check mode",
    ["provider", "mode"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000],
)

HEALTH_CHECK_SUCCESS_TOTAL = Counter(
    "bioetl_health_check_success_total",
    "Total health checks that returned HEALTHY",
    ["provider"],
)

HEALTH_CHECK_DEGRADED_TOTAL = Counter(
    "bioetl_health_check_degraded_total",
    "Total health checks that returned DEGRADED",
    ["provider"],
)

HEALTH_CHECK_FAILURES_TOTAL = Counter(
    "bioetl_health_check_failures_total",
    "Total health checks that failed or returned UNHEALTHY",
    ["provider"],
)

PROBE_MODE_FALLBACK_TOTAL = Counter(
    "bioetl_probe_mode_fallback_total",
    "Total probe-mode fallbacks that downgraded data-source health to degraded",
    ["pipeline", "component", "reason"],
)

HEALTH_CHECK_LATENCY_SECONDS = Histogram(
    "bioetl_health_check_latency_seconds",
    "Health check latency in seconds",
    ["provider"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

PREFLIGHT_MEDALLION_POLICY_VALID = Gauge(
    "bioetl_preflight_medallion_policy_valid",
    "Whether medallion policy is valid (1=valid, 0=invalid)",
    ["pipeline"],
)

PREFLIGHT_CONFIG_ERRORS_TOTAL = Gauge(
    "bioetl_preflight_config_errors_total",
    "Number of configuration errors found during preflight",
    ["pipeline"],
)
