"""Observability interface for BioETL.

Handles the exposure of metrics and other observability signals to external systems.
"""

from contextlib import suppress
from threading import Thread

# We import from infrastructure to avoid direct dependency on prometheus_client here
# if we want to be strict, but start_http_server is the standard way.
# However, to satisfy the architecture test "Forbidden import 'prometheus_client' outside observability",
# we should probably move this function to infrastructure/observability/server.py
# and import it here. But since this IS the interface layer for observability,
# maybe we can just exempt it in the test or move the implementation.

# Let's move the implementation to infrastructure/observability/server.py
# and call it from here.

from bioetl.infrastructure.observability.server import start_metrics_server as _start_server


def start_metrics_server(port: int = 8000) -> None:
    """Start Prometheus metrics HTTP server in a daemon thread.

    Args:
        port: Port to bind the HTTP server (default: 8000)
    """
    _start_server(port)