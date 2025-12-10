"""Prometheus metric name constants as Enum.

This module provides a centralized registry of all Prometheus metric names
used across BioETL components. Using an Enum ensures type safety and prevents
typos in metric names.

Naming Convention:
    - Prefix: All metrics start with ``bioetl_`` namespace
    - Snake_case: Lowercase with underscores
    - Unit suffix: Include unit when applicable (_seconds, _bytes, _total)
    - Counter suffix: All Counter metrics end with ``_total``
"""

from __future__ import annotations

from enum import Enum


class MetricName(str, Enum):
    """Prometheus metric names used across BioETL.

    All metric names follow Prometheus naming conventions:
    - https://prometheus.io/docs/practices/naming/
    - https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels

    Examples:
        >>> MetricName.CLIENT_REQUEST_TOTAL
        'bioetl_client_request_total'
        >>> MetricName.STAGE_DURATION_SECONDS.value
        'bioetl_stage_duration_seconds'
    """

    # =========================================================================
    # Stage Metrics
    # =========================================================================

    STAGE_DURATION_SECONDS = "bioetl_stage_duration_seconds"
    """Histogram: Duration of pipeline stages in seconds."""

    STAGE_TOTAL = "bioetl_stage_total"
    """Counter: Total count of pipeline stage completions by outcome."""

    # =========================================================================
    # Client Request Metrics
    # =========================================================================

    CLIENT_REQUEST_TOTAL = "bioetl_client_request_total"
    """Counter: Total client requests by provider and endpoint."""

    CLIENT_REQUEST_DURATION_SECONDS = "bioetl_client_request_duration_seconds"
    """Histogram: Duration of client requests in seconds."""

    CLIENT_REQUEST_ERRORS_TOTAL = "bioetl_client_request_errors_total"
    """Counter: Total client request errors by provider and endpoint."""

    # =========================================================================
    # Output Metrics
    # =========================================================================

    OUTPUT_WRITE_ERRORS_TOTAL = "bioetl_output_write_errors_total"
    """Counter: Total number of failed output write attempts."""


# Type alias for metric label dictionaries
MetricLabels = dict[str, str]


__all__ = [
    "MetricName",
    "MetricLabels",
]
