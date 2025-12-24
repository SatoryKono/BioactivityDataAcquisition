"""Prometheus metrics server."""

import errno
import logging
import time
from threading import Lock

from prometheus_client import start_http_server

logger = logging.getLogger(__name__)

_SERVER_STARTED = False
_SERVER_LOCK = Lock()


class MetricsServerError(Exception):
    """Raised when metrics server fails to start with fail_fast=True."""

    def __init__(
        self, port: int, reason: str, original_error: Exception | None = None
    ):
        """Initialize MetricsServerError.

        Args:
            port: Port that failed.
            reason: Reason for failure.
            original_error: Underlying exception.
        """
        super().__init__(f"Failed to start metrics server on port {port}: {reason}")


def start_metrics_server(
    port: int = 8000,
    *,
    fail_fast: bool = False,
    retry_count: int = 3,
    retry_delay: float = 1.0,
) -> bool:
    """Start Prometheus metrics HTTP server.

    Ensures the server is started only once per process.
    Run in a daemon thread (non-blocking).

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
    global _SERVER_STARTED

    if _SERVER_STARTED:
        logger.debug("Metrics server already started")
        return True

    with _SERVER_LOCK:
        if _SERVER_STARTED:
            return True

        for attempt in range(retry_count):
            try:
                start_http_server(port)
                _SERVER_STARTED = True
                logger.info(
                    "Prometheus metrics server started",
                    extra={
                        "port": port,
                        "attempt": attempt + 1,
                    },
                )
                return True
            except OSError as e:
                if e.errno == errno.EADDRINUSE:
                    # Port conflict — no retry will help
                    logger.warning(
                        "Metrics port already in use",
                        extra={
                            "port": port,
                            "errno": e.errno,
                            "action": "metrics_disabled" if not fail_fast else "failing",
                        },
                    )
                    if fail_fast:
                        raise MetricsServerError(
                            port=port,
                            reason="port_in_use",
                            original_error=e,
                        ) from e
                    # Mark as "attempted" to prevent retries, but don't pretend success
                    _SERVER_STARTED = True
                    return False
                else:
                    # Transient error — retry with backoff
                    if attempt < retry_count - 1:
                        time.sleep(retry_delay * (2**attempt))
                        continue
                    logger.error(
                        "Failed to start metrics server",
                        extra={
                            "port": port,
                            "errno": e.errno,
                            "attempts": retry_count,
                        },
                    )
                    if fail_fast:
                        raise MetricsServerError(
                            port=port,
                            reason="os_error",
                            original_error=e,
                        ) from e
                    return False
            except Exception as e:
                logger.error(
                    "Unexpected error starting metrics server",
                    extra={
                        "port": port,
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                if fail_fast:
                    raise MetricsServerError(
                        port=port,
                        reason="unexpected",
                        original_error=e,
                    ) from e
                return False

        return False  # All retries exhausted


def reset_server_state() -> None:
    """Reset server state for testing purposes only."""
    global _SERVER_STARTED
    with _SERVER_LOCK:
        _SERVER_STARTED = False
