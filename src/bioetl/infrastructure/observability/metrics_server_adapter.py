"""Adapter for metrics server operations.

Implements MetricsServerPort protocol for application layer usage.
Wraps the existing start_metrics_server infrastructure function.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.observability.server import (
    _SERVER_STARTED,
    reset_server_state,
    start_metrics_server,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class MetricsServerAdapter:
    """Adapter for metrics server operations.

    Implements the MetricsServerPort protocol for use by MetricsService.
    Wraps the infrastructure-level metrics server functions.

    Attributes:
        _logger: Optional logger for server operations.

    Example:
        >>> adapter = MetricsServerAdapter()
        >>> success = adapter.start(port=8000)
        >>> # success is True if server started
    """

    def __init__(self, logger: LoggerPort | None = None) -> None:
        """Initialize the adapter.

        Args:
            logger: Optional logger for server operations.
        """
        self._logger = logger

    def start(
        self,
        port: int = 8000,
        *,
        fail_fast: bool = False,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ) -> bool:
        """Start the metrics server.

        Args:
            port: Port to bind the HTTP server (default: 8000).
            fail_fast: If True, raise on failure.
            retry_count: Number of retries for transient errors.
            retry_delay: Delay between retries in seconds.

        Returns:
            True if server started successfully, False otherwise.
        """
        return start_metrics_server(
            port=port,
            fail_fast=fail_fast,
            retry_count=retry_count,
            retry_delay=retry_delay,
            logger=self._logger,
        )

    def is_running(self) -> bool:
        """Check if the server is currently running.

        Returns:
            True if server is running, False otherwise.
        """
        # Access the module-level state
        return _SERVER_STARTED

    def reset(self) -> None:
        """Reset server state (for testing purposes only).

        Warning:
            This should only be used in tests. In production,
            the server cannot be restarted after reset.
        """
        reset_server_state()
