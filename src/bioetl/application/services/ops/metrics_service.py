# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
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
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from bioetl.application.observability.tracing_operation_helpers import traced_operation
from bioetl.application.services.ops._metrics_service_gateway_support import (
    DeleteResult,
    PushResult,
    _MetricsGatewayMixin,
    _MetricsTracingHost,
    _MetricsTracingMixin,
)
from bioetl.domain.exceptions import BioETLError, MetricsServerError
from bioetl.domain.ports import ClockPort, MetricsPublisherPort, MetricsServerPort

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, TracingPort

# Re-export for backward compatibility
__all__ = [
    "DeleteResult",
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

    running: bool = False
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

    success: bool = False
    port: int = 0
    addr: str = "0.0.0.0"
    already_running: bool = False
    error: str | None = None


class _MetricsStartHost(_MetricsTracingHost, Protocol):
    """Structural host contract for metrics-server lifecycle helpers."""

    logger: LoggerPort
    _server: MetricsServerPort
    clock: ClockPort

    def _handle_start_error(
        self,
        port: int,
        addr: str,
        e: Exception,
        fail_fast: bool,
    ) -> StartResult: ...

    def _start_impl(
        self,
        *,
        port: int,
        addr: str,
        fail_fast: bool,
        retry_count: int,
        retry_delay: float,
    ) -> StartResult: ...


class _MetricsStatusHost(_MetricsTracingHost, Protocol):
    """Structural host contract for metrics-server status helpers."""

    _server: MetricsServerPort


class _MetricsStartMixin(_MetricsTracingMixin):
    """Metrics server start lifecycle helpers."""

    tracer: TracingPort | None = (
        None  # Any: host attr default  # Any: host attr default (PD6)
    )

    def _handle_start_error(
        self: _MetricsStartHost,
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
        self: _MetricsStartHost,
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
        if self.tracer is None:
            return self._start_impl(
                port=port,
                addr=addr,
                fail_fast=fail_fast,
                retry_count=retry_count,
                retry_delay=retry_delay,
            )
        with traced_operation(
            self.tracer,
            "metrics.start",
            self._build_span_attributes(
                operation="start",
                **{
                    "bioetl.port": port,
                    "bioetl.addr": addr,
                    "bioetl.fail_fast": fail_fast,
                },
            ),
            tracer_name=self.TRACER_NAME,
        ) as span:
            result = self._start_impl(
                port=port,
                addr=addr,
                fail_fast=fail_fast,
                retry_count=retry_count,
                retry_delay=retry_delay,
            )
            self._set_result_attributes(
                span,
                success=result.success,
                error=result.error,
                attributes={"bioetl.already_running": result.already_running},
            )
            return result

    def _start_impl(
        self: _MetricsStartHost,
        *,
        port: int,
        addr: str,
        fail_fast: bool,
        retry_count: int,
        retry_delay: float,
    ) -> StartResult:
        """Implement metrics server startup without tracing concerns."""
        self.logger.debug(
            "Starting metrics server",
            port=port,
            addr=addr,
            fail_fast=fail_fast,
        )

        runtime_status = self._server.get_runtime_status()
        if runtime_status.running:
            self.logger.debug("Metrics server already running")
            return StartResult(
                success=True,
                port=runtime_status.port or port,
                addr=runtime_status.addr or addr,
                already_running=True,
            )

        try:
            success = self._server.start(
                port=port,
                addr=addr,
                started_at=self.clock.now(),
                fail_fast=fail_fast,
                retry_count=retry_count,
                retry_delay=retry_delay,
            )
            if success:
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


class _MetricsStatusMixin(_MetricsTracingMixin):
    """Metrics server status helpers."""

    tracer: TracingPort | None = (
        None  # Any: host attr default  # Any: host attr default (PD6)
    )

    def get_status(self: _MetricsStatusHost) -> MetricsServerStatus:
        """Get the current status of the metrics server.

        Returns:
            MetricsServerStatus with current state.

        Example:
            >>> status = service.get_status()
            >>> if status.running:
            ...     logger.info("Server running", port=status.port)
        """
        if self.tracer is None:
            runtime_status = self._server.get_runtime_status()
            return MetricsServerStatus(
                running=runtime_status.running,
                port=runtime_status.port,
                started_at=runtime_status.started_at,
            )
        with traced_operation(
            self.tracer,
            "metrics.get_status",
            self._build_span_attributes(operation="get_status"),
            tracer_name=self.TRACER_NAME,
        ) as span:
            runtime_status = self._server.get_runtime_status()
            self._set_result_attributes(
                span,
                success=True,
                attributes={"bioetl.running": runtime_status.running},
            )
            return MetricsServerStatus(
                running=runtime_status.running,
                port=runtime_status.port,
                started_at=runtime_status.started_at,
            )

    def is_running(self: _MetricsStatusHost) -> bool:
        """Check if the metrics server is currently running.

        Returns:
            True if server is running, False otherwise.
        """
        return bool(self._server.is_running())


@dataclass
class MetricsService(
    _MetricsStartMixin,
    _MetricsStatusMixin,
    _MetricsGatewayMixin,
):
    """Service for metrics server operations."""

    logger: LoggerPort
    _server: MetricsServerPort
    clock: ClockPort
    tracer: TracingPort | None = None
    _publisher: MetricsPublisherPort | None = field(default=None, repr=False)
