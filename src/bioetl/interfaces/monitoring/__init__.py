"""Monitoring interface helpers exposing Prometheus-backed metrics ports."""

from bioetl.domain.observability.contracts import MetricsPortABC
from bioetl.infrastructure.observability import metrics as prometheus_metrics
from bioetl.infrastructure.observability.factories import create_metrics_port
from bioetl.infrastructure.observability.server import start_metrics_server_once


def create_prometheus_metrics_port() -> MetricsPortABC:
    """Create metrics port wired to Prometheus collectors."""

    return create_metrics_port()


__all__ = [
    "create_prometheus_metrics_port",
    "prometheus_metrics",
    "start_metrics_server_once",
]
