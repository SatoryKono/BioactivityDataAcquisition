"""Prometheus metrics used across BioETL components."""

from prometheus_client import Counter, Histogram

__all__ = [
    "STAGE_DURATION_SECONDS",
    "STAGE_TOTAL",
    "HTTP_REQUESTS_TOTAL",
    "HTTP_LATENCY_SECONDS",
]

STAGE_DURATION_SECONDS = Histogram(
    "bioetl_stage_duration_seconds",
    "Duration of pipeline stages in seconds.",
    ["pipeline", "provider", "entity", "stage", "outcome"],
)

STAGE_TOTAL = Counter(
    "bioetl_stage_total",
    "Total count of pipeline stage completions by outcome.",
    ["pipeline", "provider", "entity", "stage", "outcome"],
)

HTTP_REQUESTS_TOTAL = Counter(
    "bioetl_http_requests_total",
    "Total HTTP requests performed by BioETL clients.",
    ["provider", "endpoint", "method", "status_class"],
)

HTTP_LATENCY_SECONDS = Histogram(
    "bioetl_http_latency_seconds",
    "HTTP request latency in seconds.",
    ["provider", "endpoint", "method", "status_class"],
)
