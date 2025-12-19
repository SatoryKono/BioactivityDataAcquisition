"""Observability interface for BioETL.

Handles the exposure of metrics and other observability signals to external systems.
"""

from contextlib import suppress
from threading import Thread

from prometheus_client import start_http_server


def start_metrics_server(port: int = 8000) -> None:
    """Start Prometheus metrics HTTP server in a daemon thread.

    Args:
        port: Port to bind the HTTP server (default: 8000)
    """
    # prometheus_client.start_http_server starts a daemon thread by default
    # but we wrap it to ensure we handle any immediate errors if needed
    # and to clarify intent.
    try:
        start_http_server(port)
    except OSError as e:
        # If port is in use, we might want to log it but not crash?
        # The original code returned False.
        # But here we are in the Interface layer, we should probably let the caller handle exceptions
        # or log them.
        # Re-raising for now to let CLI handle it.
        raise e
