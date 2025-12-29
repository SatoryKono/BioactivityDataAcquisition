"""Observability interface for BioETL.

Handles the exposure of metrics and other observability signals to external systems.
"""

from __future__ import annotations

from bioetl.infrastructure.observability.server import (
    MetricsServerError,
)
from bioetl.infrastructure.observability.server import (
    start_metrics_server as _start_server,
)

__all__ = [
    "MetricsServerError",
    "start_metrics_server",
]


def start_metrics_server(
    port: int = 8000,
    *,
    fail_fast: bool = False,
    retry_count: int = 3,
    retry_delay: float = 1.0,
) -> bool:
    """Start Prometheus metrics HTTP server in a daemon thread.

    Args:
        port: Port to bind the HTTP server (default: 8000)
        fail_fast: If True, raise MetricsServerError on failure
        retry_count: Number of retries for transient errors (default: 3)
        retry_delay: Delay between retries in seconds (default: 1.0)

    Returns:
        True if server started successfully, False otherwise

    Raises:
        MetricsServerError: If fail_fast=True and server cannot start
    """
    return _start_server(
        port=port,
        fail_fast=fail_fast,
        retry_count=retry_count,
        retry_delay=retry_delay,
    )
