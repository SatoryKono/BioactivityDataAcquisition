"""Monitoring interface helpers exposing Prometheus-backed metrics ports."""

from bioetl.infrastructure.observability import metrics as prometheus_metrics
from bioetl.infrastructure.observability.factories import default_metrics_port
from bioetl.infrastructure.observability.server import start_metrics_server_once
from bioetl.interfaces.observability import MetricsPortABC


def create_prometheus_metrics_port() -> MetricsPortABC:
    """Create metrics port wired to Prometheus collectors."""

    return default_metrics_port()


__all__ = [
    "create_prometheus_metrics_port",
    "prometheus_metrics",
    "start_metrics_server_once",
]
