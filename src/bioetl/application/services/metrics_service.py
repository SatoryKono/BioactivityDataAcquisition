"""Metrics service for application-layer metrics server management.

Provides high-level operations for managing the Prometheus metrics server.
Abstracts infrastructure concerns from CLI and other interfaces.

Implements RULES.md §1.1 - Application layer depends only on Domain.

Note:
    MetricsServerError is defined in domain.exceptions.critical
    and re-exported here for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.domain.exceptions import BioETLError, MetricsServerError
from bioetl.domain.ports import MetricsPublisherPort, MetricsServerPort

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

# Re-export for backward compatibility
__all__ = [
    "MetricsPublisherPort",
    "MetricsServerError",
    "MetricsServerPort",
    "MetricsServerStatus",
    "MetricsService",
    "PushResult",
    "StartResult",
]

_METRICS_START_ERRORS = (
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


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
    addr: str = "0.0.0.0"
    already_running: bool = False
    error: str | None = None


@dataclass(frozen=True, slots=True)
class PushResult:
    """Result of publishing metrics to an external gateway."""

    success: bool
    gateway: str
    run_label: str
    grouping_key: dict[str, str]
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
    _publisher: MetricsPublisherPort | None = field(default=None, repr=False)
    _port: int | None = field(default=None, repr=False)
    _started_at: datetime | None = field(default=None, repr=False)

    def _handle_start_error(
        self,
        port: int,
        addr: str,
        e: Exception,
        fail_fast: bool,
    ) -> StartResult:
        """Handle error during server start.

        Args:
            port: Port number that the server attempted to bind.
            e: Exception raised during the start attempt.
            fail_fast: When True, re-raises the error as MetricsServerError instead
                of returning a failure result.

        Returns:
            StartResult with ``success=False`` and the error message, when fail_fast is False.
        """
        error_msg = str(e)
        self.logger.error(
            "Metrics server error",
            port=port,
            addr=addr,
            error=error_msg,
            error_type=type(e).__name__,
        )
        if fail_fast:
            raise MetricsServerError(
                port=port, reason=error_msg, original_error=e
            ) from e
        return StartResult(success=False, port=port, addr=addr, error=error_msg)

    def start(
        self,
        port: int = 8000,
        addr: str = "0.0.0.0",
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
        self.logger.debug(
            "Starting metrics server",
            port=port,
            addr=addr,
            fail_fast=fail_fast,
        )

        if self._server.is_running():
            self.logger.debug("Metrics server already running")
            return StartResult(
                success=True,
                port=self._port or port,
                addr=addr,
                already_running=True,
            )

        try:
            success = self._server.start(
                port=port,
                addr=addr,
                fail_fast=fail_fast,
                retry_count=retry_count,
                retry_delay=retry_delay,
            )
            if success:
                object.__setattr__(self, "_port", port)
                object.__setattr__(self, "_started_at", datetime.now(tz=UTC))
                self.logger.info("Metrics server started", port=port, addr=addr)
                return StartResult(success=True, port=port, addr=addr)

            self.logger.warning("Metrics server failed to start", port=port, addr=addr)
            return StartResult(
                success=False,
                port=port,
                addr=addr,
                error="Failed to bind port",
            )
        except _METRICS_START_ERRORS as e:
            return self._handle_start_error(port, addr, e, fail_fast)

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

    def push_to_gateway(
        self,
        *,
        gateway: str,
        run_label: str = "bioetl",
        grouping_key: dict[str, str] | None = None,
    ) -> PushResult:
        """Publish current metrics snapshot through the explicit publisher port."""
        labels = dict(grouping_key or {})
        if self._publisher is None:
            error = "Metrics publisher is not configured"
            self.logger.warning(
                "Metrics gateway publication unavailable",
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
                error=error,
            )
            return PushResult(
                success=False,
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
                error=error,
            )

        try:
            success = self._publisher.push_to_gateway(
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
            )
        except _METRICS_START_ERRORS as exc:
            error = str(exc)
            self.logger.warning(
                "Metrics gateway publication failed",
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
                error=error,
                error_type=type(exc).__name__,
            )
            return PushResult(
                success=False,
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
                error=error,
            )

        if success:
            self.logger.info(
                "Metrics gateway publication completed",
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
            )
            return PushResult(
                success=True,
                gateway=gateway,
                run_label=run_label,
                grouping_key=labels,
            )

        error = "Publisher returned unsuccessful result"
        self.logger.warning(
            "Metrics gateway publication failed",
            gateway=gateway,
            run_label=run_label,
            grouping_key=labels,
            error=error,
        )
        return PushResult(
            success=False,
            gateway=gateway,
            run_label=run_label,
            grouping_key=labels,
            error=error,
        )
