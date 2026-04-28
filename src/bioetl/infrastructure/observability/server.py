"""Prometheus metrics server."""

from __future__ import annotations

import errno
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import TYPE_CHECKING

from prometheus_client import REGISTRY, start_http_server
from prometheus_client.exposition import pushadd_to_gateway

from bioetl.domain.exceptions import MetricsServerError
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@dataclass(slots=True)
class _MetricsServerRuntimeState:
    """In-process metrics server state.

    The HTTP server itself is still process-scoped, but its mutable started/lock
    bookkeeping stays behind one explicit state object instead of free globals.
    """

    started: bool = False
    lock: Lock = field(default_factory=Lock)


_SERVER_RUNTIME = _MetricsServerRuntimeState()

# Re-export for backward compatibility
__all__ = [
    "MetricsServerError",
    "is_metrics_server_running",
    "push_metrics_to_gateway",
    "reset_server_state",
    "start_metrics_server",
]


def _handle_port_in_use(
    port: int, e: OSError, fail_fast: bool, logger: LoggerPort
) -> bool:
    """Handle port already in use error.

    Returns:
        False to indicate the server was not started on a new port.
    """
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
    return False


def _handle_os_error(
    port: int, e: OSError, retry_count: int, fail_fast: bool, logger: LoggerPort
) -> bool:
    """Handle transient OS error after all retries exhausted.

    Returns:
        False to indicate server startup failed.
    """
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
    """Handle unexpected errors during server startup.

    Returns:
        False to indicate server startup failed.
    """
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
    addr: str = "0.0.0.0",
    *,
    fail_fast: bool = False,
    retry_count: int = 3,
    retry_delay: float = 1.0,
    logger: LoggerPort | None = None,
) -> bool:
    """Start Prometheus metrics server once with retry and optional fail-fast.

    Returns:
        True if server started successfully or was already running, False otherwise.
    """

    if logger is None:
        logger = NoOpLogger()

    if _SERVER_RUNTIME.started:
        logger.debug("Metrics server already started")
        return True

    with _SERVER_RUNTIME.lock:
        if _SERVER_RUNTIME.started:
            return True

        for attempt in range(retry_count):
            try:
                start_http_server(port, addr=addr)
                _SERVER_RUNTIME.started = True
                logger.info(
                    "Prometheus metrics server started",
                    port=port,
                    addr=addr,
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
            except (RuntimeError, ValueError, TypeError, AttributeError) as e:
                return _handle_unexpected_error(port, e, fail_fast, logger)

        return False


def is_metrics_server_running() -> bool:
    """Return the live in-process metrics server state."""
    return _SERVER_RUNTIME.started


def push_metrics_to_gateway(
    gateway: str | None = None,
    run_label: str = "bioetl",
    logger: LoggerPort | None = None,
    grouping_key: dict[str, str] | None = None,
    job: str | None = None,
) -> bool:
    """Push current metrics to Prometheus Pushgateway.

    Preserves metrics after batch pipeline exits so Grafana
    dashboards continue to display data.

    Uses grouping_key to isolate metrics per pipeline so that
    successive pipeline runs don't overwrite each other's data.

    Args:
        gateway: Pushgateway URL (default: from BIOETL_PUSHGATEWAY_URL
                 env var, or 'localhost:9091').
        run_label: Run label for pushed metrics.
        logger: Structured logger.
        grouping_key: Additional grouping labels (e.g. {"pipeline": "chembl_molecule"}).
        job: Backward-compatible alias for run_label.

    Returns:
        True if push succeeded, False otherwise.

    """
    if logger is None:
        logger = NoOpLogger()

    gateway = gateway or "localhost:9091"
    effective_run_label = job if job is not None else run_label

    try:
        # Keep Pushgateway publication best-effort so CLI teardown does not stall
        # for tens of seconds when no local gateway is running.
        pushadd_to_gateway(
            gateway,
            job=effective_run_label,
            registry=REGISTRY,
            grouping_key=grouping_key or {},
            timeout=1.0,
        )
        logger.info(
            "Metrics pushed to gateway",
            gateway=gateway,
            run_label=effective_run_label,
            grouping_key=grouping_key,
        )
        return True
    except (
        OSError,
        ConnectionError,
        TimeoutError,
        RuntimeError,
        ValueError,
        TypeError,
    ) as e:
        logger.warning(
            "Failed to push metrics to gateway",
            gateway=gateway,
            error=str(e),
        )
        return False


def reset_server_state() -> None:
    """Reset server state for testing purposes only."""
    with _SERVER_RUNTIME.lock:
        _SERVER_RUNTIME.started = False
