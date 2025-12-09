"""Prometheus metrics used across BioETL components."""

from prometheus_client import Counter, Histogram

__all__ = [
    "STAGE_DURATION_SECONDS",
    "STAGE_TOTAL",
    "HTTP_REQUESTS_TOTAL",
    "HTTP_LATENCY_SECONDS",
    "CLIENT_REQUEST_TOTAL",
    "CLIENT_REQUEST_DURATION_SECONDS",
    "CLIENT_REQUEST_ERRORS",
    "OUTPUT_WRITE_ERRORS_TOTAL",
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

CLIENT_REQUEST_TOTAL = Counter(
    "client_request_total",
    "Total client requests by provider and endpoint.",
    ["provider", "endpoint", "status"],
)

CLIENT_REQUEST_DURATION_SECONDS = Histogram(
    "client_request_duration_seconds",
    "Duration of client requests in seconds.",
    ["provider", "endpoint", "status"],
)

CLIENT_REQUEST_ERRORS = Counter(
    "client_request_errors",
    "Total client request errors by provider and endpoint.",
    ["provider", "endpoint", "status"],
)

OUTPUT_WRITE_ERRORS_TOTAL = Counter(
    "output_write_errors_total",
    "Total number of failed output write attempts.",
    ["entity", "error_type"],
)
