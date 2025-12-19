"""Prometheus metrics server."""

from prometheus_client import start_http_server


def start_metrics_server(port: int = 8000) -> None:
    """Start Prometheus metrics HTTP server.

    Args:
        port: Port to bind the HTTP server (default: 8000)
    """
    start_http_server(port)
