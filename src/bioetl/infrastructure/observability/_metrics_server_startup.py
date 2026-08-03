"""Prometheus metrics server startup helpers."""

from __future__ import annotations

import errno
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.exceptions import MetricsServerError
from bioetl.infrastructure.observability._metrics_gateway_publication import (
    _emit_metrics_publication_event,
    _PublicationMetric,
)
from bioetl.infrastructure.observability._metrics_server_state import (
    _SERVER_RUNTIME,
    mark_metrics_server_started,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

__all__ = ["start_metrics_server_runtime"]


def _handle_port_in_use(
    *,
    port: int,
    error: OSError,
    fail_fast: bool,
    logger: LoggerPort,
    publication_metric: _PublicationMetric,
) -> bool:
    """Handle port already in use error."""
    logger.warning(
        "Metrics port already in use",
        port=port,
        errno=error.errno,
        action="metrics_disabled" if not fail_fast else "failing",
    )
    _emit_metrics_publication_event(
        grouping_key=None,
        target="metrics_server",
        status="failed",
        publication_metric=publication_metric,
    )
    if fail_fast:
        raise MetricsServerError(
            port=port,
            reason="port_in_use",
            original_error=error,
        ) from error
    return False


def _handle_os_error(
    *,
    port: int,
    error: OSError,
    retry_count: int,
    fail_fast: bool,
    logger: LoggerPort,
    publication_metric: _PublicationMetric,
) -> bool:
    """Handle transient OS error after all retries are exhausted."""
    logger.error(
        "Failed to start metrics server",
        port=port,
        errno=error.errno,
        attempts=retry_count,
    )
    _emit_metrics_publication_event(
        grouping_key=None,
        target="metrics_server",
        status="failed",
        publication_metric=publication_metric,
    )
    if fail_fast:
        raise MetricsServerError(
            port=port,
            reason="os_error",
            original_error=error,
        ) from error
    return False


def _handle_unexpected_error(
    *,
    port: int,
    error: Exception,
    fail_fast: bool,
    logger: LoggerPort,
    publication_metric: _PublicationMetric,
) -> bool:
    """Handle unexpected errors during server startup."""
    logger.error(
        "Unexpected error starting metrics server",
        port=port,
        error_type=type(error).__name__,
    )
    _emit_metrics_publication_event(
        grouping_key=None,
        target="metrics_server",
        status="failed",
        publication_metric=publication_metric,
    )
    if fail_fast:
        raise MetricsServerError(
            port=port,
            reason="unexpected",
            original_error=error,
        ) from error
    return False


def start_metrics_server_runtime(
    *,
    start_http_server_fn: Callable[..., object],
    sleep_fn: Callable[[float], object],
    publication_metric: _PublicationMetric,
    port: int = 8000,
    addr: str = "0.0.0.0",
    started_at: datetime | None = None,
    fail_fast: bool = False,
    retry_count: int = 3,
    retry_delay: float = 1.0,
    logger: LoggerPort | None = None,
) -> bool:
    """Start Prometheus metrics server once with retry and optional fail-fast."""
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
                start_http_server_fn(port, addr=addr)
                mark_metrics_server_started(
                    port=port,
                    addr=addr,
                    started_at=started_at,
                )
                logger.info(
                    "Prometheus metrics server started",
                    port=port,
                    addr=addr,
                    attempt=attempt + 1,
                )
                _emit_metrics_publication_event(
                    grouping_key=None,
                    target="metrics_server",
                    status="success",
                    publication_metric=publication_metric,
                )
                return True
            except OSError as error:
                if error.errno == errno.EADDRINUSE:
                    return _handle_port_in_use(
                        port=port,
                        error=error,
                        fail_fast=fail_fast,
                        logger=logger,
                        publication_metric=publication_metric,
                    )
                if attempt < retry_count - 1:
                    sleep_fn(retry_delay * (2**attempt))
                    continue
                return _handle_os_error(
                    port=port,
                    error=error,
                    retry_count=retry_count,
                    fail_fast=fail_fast,
                    logger=logger,
                    publication_metric=publication_metric,
                )
            except (RuntimeError, ValueError, TypeError, AttributeError) as error:
                return _handle_unexpected_error(
                    port=port,
                    error=error,
                    fail_fast=fail_fast,
                    logger=logger,
                    publication_metric=publication_metric,
                )

        return False
