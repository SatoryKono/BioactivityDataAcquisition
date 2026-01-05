"""Metrics service for application-layer metrics server management.

Provides high-level operations for managing the Prometheus metrics server.
Abstracts infrastructure concerns from CLI and other interfaces.

Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class MetricsServerError(Exception):
    """Raised when metrics server fails to start."""

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


@runtime_checkable
class MetricsServerPort(Protocol):
    """Protocol for metrics server operations.

    Abstracts the metrics server infrastructure for application layer.
    """

    def start(
        self,
        port: int,
        *,
        fail_fast: bool = False,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ) -> bool:
        """Start the metrics server.

        Args:
            port: Port to bind the HTTP server.
            fail_fast: If True, raise on failure.
            retry_count: Number of retries for transient errors.
            retry_delay: Delay between retries in seconds.

        Returns:
            True if server started successfully, False otherwise.
        """
        ...

    def is_running(self) -> bool:
        """Check if the server is currently running."""
        ...

    def reset(self) -> None:
        """Reset server state (for testing purposes)."""
        ...


@dataclass(frozen=True, slots=True)
class MetricsServerStatus:
    """Status of the metrics server.

    Attributes:
        running: Whether the server is running.
        port: Port the server is bound to (if running).
        started_at: When the server was started.
        error: Error message if server failed to start.
    """

    running: bool
    port: int | None = None
    started_at: datetime | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class StartResult:
    """Result of starting the metrics server.

    Attributes:
        success: Whether the server started successfully.
        port: Port the server is bound to.
        already_running: True if server was already running.
        error: Error message if failed.
    """

    success: bool
    port: int
    already_running: bool = False
    error: str | None = None


@dataclass
class MetricsService:
    """Service for metrics server operations.

    Provides high-level operations for managing the Prometheus metrics
    server used by CLI and other interfaces. Abstracts infrastructure
    details for Application-layer abstraction.

    Attributes:
        logger: Structured logger for observability.
        _server: Metrics server port implementation.
        _port: Current configured port.
        _started_at: Timestamp when server was started.

    Example:
        >>> service = MetricsService(logger=logger, _server=server_adapter)
        >>> result = service.start(port=8000)
        >>> if result.success:
        ...     logger.info("Metrics server started", port=result.port)
    """

    logger: LoggerPort
    _server: MetricsServerPort
    _port: int | None = field(default=None, repr=False)
    _started_at: datetime | None = field(default=None, repr=False)

    def _handle_start_error(
        self, port: int, e: Exception, fail_fast: bool
    ) -> StartResult:
        """Handle error during server start."""
        error_msg = str(e)
        self.logger.error(
            "Metrics server error",
            port=port,
            error=error_msg,
            error_type=type(e).__name__,
        )
        if fail_fast:
            raise MetricsServerError(
                port=port, reason=error_msg, original_error=e
            ) from e
        return StartResult(success=False, port=port, error=error_msg)

    def start(
        self,
        port: int = 8000,
        *,
        fail_fast: bool = False,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ) -> StartResult:
        """Start the Prometheus metrics server.

        Idempotent operation - safe to call multiple times.

        Args:
            port: Port to bind the HTTP server (default: 8000).
            fail_fast: If True, raise MetricsServerError on failure.
            retry_count: Number of retries for transient errors (default: 3).
            retry_delay: Delay between retries in seconds (default: 1.0).

        Returns:
            StartResult with operation status.

        Raises:
            MetricsServerError: If fail_fast=True and server cannot start.
        """
        self.logger.debug("Starting metrics server", port=port, fail_fast=fail_fast)

        if self._server.is_running():
            self.logger.debug("Metrics server already running")
            return StartResult(
                success=True, port=self._port or port, already_running=True
            )

        try:
            success = self._server.start(
                port=port,
                fail_fast=fail_fast,
                retry_count=retry_count,
                retry_delay=retry_delay,
            )
            if success:
                object.__setattr__(self, "_port", port)
                object.__setattr__(self, "_started_at", datetime.now(tz=UTC))
                self.logger.info("Metrics server started", port=port)
                return StartResult(success=True, port=port)

            self.logger.warning("Metrics server failed to start", port=port)
            return StartResult(success=False, port=port, error="Failed to bind port")
        except Exception as e:
            return self._handle_start_error(port, e, fail_fast)

    def get_status(self) -> MetricsServerStatus:
        """Get the current status of the metrics server.

        Returns:
            MetricsServerStatus with current state.

        Example:
            >>> status = service.get_status()
            >>> if status.running:
            ...     logger.info("Server running", port=status.port)
        """
        running = self._server.is_running()
        return MetricsServerStatus(
            running=running,
            port=self._port if running else None,
            started_at=self._started_at if running else None,
        )

    def is_running(self) -> bool:
        """Check if the metrics server is currently running.

        Returns:
            True if server is running, False otherwise.
        """
        return self._server.is_running()
