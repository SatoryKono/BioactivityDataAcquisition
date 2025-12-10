"""Prometheus metrics used across BioETL components.

Naming Convention
-----------------
All metrics MUST follow these rules:

1. **Prefix**: All metrics start with ``bioetl_`` to namespace them
2. **Snake_case**: Use lowercase with underscores
   (e.g., ``bioetl_stage_duration_seconds``)
3. **Unit suffix**: Include unit as suffix when applicable
   (``_seconds``, ``_bytes``, ``_total``)
4. **Counter suffix**: All Counter metrics end with ``_total``
5. **Descriptive names**: Use clear, descriptive names that indicate
   what is being measured

Examples:
    - ``bioetl_stage_duration_seconds`` (Histogram with unit)
    - ``bioetl_client_request_total`` (Counter with _total suffix)
    - ``bioetl_output_write_errors_total`` (Counter for errors)

References:
    - https://prometheus.io/docs/practices/naming/
    - https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels

Note:
    Metric names are centralized in infrastructure.settings.metrics.MetricName.
"""

from prometheus_client import Counter, Histogram

from bioetl.infrastructure.settings.metrics import MetricName

__all__ = [
    # Stage metrics
    "STAGE_DURATION_SECONDS",
    "STAGE_TOTAL",
    # Client request metrics
    "CLIENT_REQUEST_TOTAL",
    "CLIENT_REQUEST_DURATION_SECONDS",
    "CLIENT_REQUEST_ERRORS_TOTAL",
    # Output metrics
    "OUTPUT_WRITE_ERRORS_TOTAL",
]

# =============================================================================
# Stage Metrics
# =============================================================================

STAGE_DURATION_SECONDS = Histogram(
    MetricName.STAGE_DURATION_SECONDS.value,
    "Duration of pipeline stages in seconds.",
    ["pipeline", "provider", "entity", "stage", "outcome"],
)

STAGE_TOTAL = Counter(
    MetricName.STAGE_TOTAL.value,
    "Total count of pipeline stage completions by outcome.",
    ["pipeline", "provider", "entity", "stage", "outcome"],
)

# =============================================================================
# Client Request Metrics
# =============================================================================

CLIENT_REQUEST_TOTAL = Counter(
    MetricName.CLIENT_REQUEST_TOTAL.value,
    "Total client requests by provider and endpoint.",
    ["provider", "endpoint", "status"],
)

CLIENT_REQUEST_DURATION_SECONDS = Histogram(
    MetricName.CLIENT_REQUEST_DURATION_SECONDS.value,
    "Duration of client requests in seconds.",
    ["provider", "endpoint", "status"],
)

CLIENT_REQUEST_ERRORS_TOTAL = Counter(
    MetricName.CLIENT_REQUEST_ERRORS_TOTAL.value,
    "Total client request errors by provider and endpoint.",
    ["provider", "endpoint", "status"],
)

# =============================================================================
# Output Metrics
# =============================================================================

OUTPUT_WRITE_ERRORS_TOTAL = Counter(
    MetricName.OUTPUT_WRITE_ERRORS_TOTAL.value,
    "Total number of failed output write attempts.",
    ["entity", "error_type"],
)
