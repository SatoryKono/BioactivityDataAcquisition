"""Prometheus metrics server."""

import errno
import logging
from threading import Lock
from typing import Optional

from prometheus_client import start_http_server

logger = logging.getLogger(__name__)

_SERVER_PORT: Optional[int] = None
_SERVER_LOCK = Lock()


def _raise_port_conflict_error(current_port: int, requested_port: int) -> None:
    """Raise RuntimeError when server is running on a different port.
    
    Args:
        current_port: Port on which server is currently running
        requested_port: Port that was requested to start
        
    Raises:
        RuntimeError: Always raises with descriptive error message
    """
    error_msg = (
        f"Metrics server already running on port {current_port}, "
        f"cannot start on port {requested_port}"
    )
    logger.error(error_msg)
    raise RuntimeError(error_msg)


def start_metrics_server(port: int = 8000) -> None:
    """Start Prometheus metrics HTTP server.

    Ensures the server is started only once per process on the specified port.
    Run in a daemon thread (non-blocking).

    Args:
        port: Port to bind the HTTP server (default: 8000)

    Raises:
        RuntimeError: If server is already running on a different port
        OSError: If port is already in use by another process
    """
    global _SERVER_PORT

    # Check if server is already running
    if _SERVER_PORT is not None:
        if _SERVER_PORT == port:
            logger.debug(f"Metrics server already started on port {port}")
            return
        else:
            _raise_port_conflict_error(_SERVER_PORT, port)

    with _SERVER_LOCK:
        # Double-check after acquiring lock
        if _SERVER_PORT is not None:
            if _SERVER_PORT == port:
                return
            else:
                _raise_port_conflict_error(_SERVER_PORT, port)

        try:
            start_http_server(port)
            _SERVER_PORT = port
            logger.info(f"Prometheus metrics server started on port {port}")
        except OSError as e:
            # Handle "Address already in use" - this is a fatal error
            if e.errno == errno.EADDRINUSE:
                error_msg = (
                    f"Port {port} is already in use by another process. "
                    f"Metrics server cannot be started. Please check if another "
                    f"instance is running or choose a different port."
                )
                logger.error(error_msg, exc_info=True)
                raise OSError(e.errno, error_msg) from e
            else:
                logger.error(f"Failed to start metrics server on port {port}: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error starting metrics server: {e}")
            raise
