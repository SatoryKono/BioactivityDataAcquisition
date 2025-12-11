"""Monitoring interface for BioETL metrics export.

This module provides Prometheus-backed metrics integration for observability.

Key components:
    - create_prometheus_metrics_port(): Factory for MetricsPortABC implementation
    - prometheus_metrics: Direct access to Prometheus collectors module
    - start_metrics_server_once(): Helper to start HTTP metrics endpoint

Example usage:
    from bioetl.interfaces.monitoring import (
        create_prometheus_metrics_port,
        start_metrics_server_once,
    )

    # Create metrics port for injection
    metrics = create_prometheus_metrics_port()

    # Start HTTP server for Prometheus scraping (default port 9090)
    start_metrics_server_once()
"""

from bioetl.domain.observability.contracts import MetricsPortABC
from bioetl.infrastructure.observability import metrics as prometheus_metrics
from bioetl.infrastructure.observability.factories import create_metrics_port
from bioetl.infrastructure.observability.server import start_metrics_server_once


def create_prometheus_metrics_port() -> MetricsPortABC:
    """Create metrics port wired to Prometheus collectors."""
    return create_metrics_port()


__all__ = [
    # Factory
    "create_prometheus_metrics_port",
    # Direct access to infrastructure
    "prometheus_metrics",
    "start_metrics_server_once",
]
