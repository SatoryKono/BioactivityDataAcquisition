"""Prometheus metrics server."""

from __future__ import annotations

import errno
import time
from threading import Lock
from typing import TYPE_CHECKING

from prometheus_client import start_http_server

from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

_SERVER_STARTED = False
_SERVER_LOCK = Lock()


class MetricsServerError(Exception):
    """Raised when metrics server fails to start with fail_fast=True."""

    def __init__(self, port: int, reason: str, original_error: Exception | None = None):
        """Initialize MetricsServerError.

        Args:
            port: Port that failed.
            reason: Reason for failure.
            original_error: Underlying exception.

        """
        super().__init__(f"Failed to start metrics server on port {port}: {reason}")
        self.port = port
        self.reason = reason
        self.original_error = original_error


def _handle_port_in_use(
    port: int, e: OSError, fail_fast: bool, logger: LoggerPort
) -> bool:
    """Handle port already in use error."""
    global _SERVER_STARTED
    logger.warning(
        "Metrics port already in use",
        port=port,
        errno=e.errno,
        action="metrics_disabled" if not fail_fast else "failing",
    )
    if fail_fast:
        raise MetricsServerError(
            port=port,
            reason="port_in_use",
            original_error=e,
        ) from e
    _SERVER_STARTED = True
    return False


def _handle_os_error(
    port: int, e: OSError, retry_count: int, fail_fast: bool, logger: LoggerPort
) -> bool:
    """Handle transient OS error after all retries exhausted."""
    logger.error(
        "Failed to start metrics server",
        port=port,
        errno=e.errno,
        attempts=retry_count,
    )
    if fail_fast:
        raise MetricsServerError(port=port, reason="os_error", original_error=e) from e
    return False


def _handle_unexpected_error(
    port: int, e: Exception, fail_fast: bool, logger: LoggerPort
) -> bool:
    """Handle unexpected errors during server startup."""
    logger.error(
        "Unexpected error starting metrics server",
        port=port,
        error_type=type(e).__name__,
    )
    if fail_fast:
        raise MetricsServerError(
            port=port, reason="unexpected", original_error=e
        ) from e
    return False


def start_metrics_server(
    port: int = 8000,
    *,
    fail_fast: bool = False,
    retry_count: int = 3,
    retry_delay: float = 1.0,
    logger: LoggerPort | None = None,
) -> bool:
    """Start Prometheus metrics HTTP server.

    Ensures the server is started only once per process.
    Run in a daemon thread (non-blocking).

    Args:
        port: Port to bind the HTTP server (default: 8000)
        fail_fast: If True, raise MetricsServerError on failure
        retry_count: Number of retries for transient errors (default: 3)
        retry_delay: Delay between retries in seconds (default: 1.0)
        logger: Structured logger for observability. If None, uses NoOpLogger.

    Returns:
        True if server started successfully, False otherwise

    Raises:
        MetricsServerError: If fail_fast=True and server cannot start

    """
    global _SERVER_STARTED

    if logger is None:
        logger = NoOpLogger()

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
                    port=port,
                    attempt=attempt + 1,
                )
                return True
            except OSError as e:
                if e.errno == errno.EADDRINUSE:
                    return _handle_port_in_use(port, e, fail_fast, logger)
                if attempt < retry_count - 1:
                    time.sleep(retry_delay * (2**attempt))
                    continue
                return _handle_os_error(port, e, retry_count, fail_fast, logger)
            except Exception as e:
                return _handle_unexpected_error(port, e, fail_fast, logger)

        return False


def reset_server_state() -> None:
    """Reset server state for testing purposes only."""
    global _SERVER_STARTED
    with _SERVER_LOCK:
        _SERVER_STARTED = False
