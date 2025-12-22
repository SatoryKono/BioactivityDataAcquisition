"""Prometheus metrics server."""

import errno
import logging
from threading import Lock

from prometheus_client import start_http_server

logger = logging.getLogger(__name__)

_SERVER_STARTED = False
_SERVER_LOCK = Lock()


def start_metrics_server(port: int = 8000) -> None:
    """Start Prometheus metrics HTTP server.

    Ensures the server is started only once per process.
    Run in a daemon thread (non-blocking).

    Args:
        port: Port to bind the HTTP server (default: 8000)
    """
    global _SERVER_STARTED

    if _SERVER_STARTED:
        logger.debug("Metrics server already started")
        return

    with _SERVER_LOCK:
        if _SERVER_STARTED:
            return

        try:
            start_http_server(port)
            _SERVER_STARTED = True
            logger.info(f"Prometheus metrics server started on port {port}")
        except OSError as e:
            # Handle "Address already in use" gracefully
            if e.errno == errno.EADDRINUSE:
                logger.warning(
                    f"Port {port} is already in use. Metrics server might be running in another process or instance."
                )
                # We mark it as started to avoid retrying in this process
                _SERVER_STARTED = True
            else:
                logger.error(f"Failed to start metrics server on port {port}: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error starting metrics server: {e}")
            raise
