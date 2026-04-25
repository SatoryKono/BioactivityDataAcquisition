"""Metrics service for application-layer metrics server management.

Provides high-level operations for managing the Prometheus metrics server.
Abstracts infrastructure concerns from CLI and other interfaces.

Implements RULES.md §1.1 - Application layer depends only on Domain.

Note:
    MetricsServerError is defined in domain.exceptions.critical
    and re-exported here for backward compatibility.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.application.observability.span_attribute_values import (
    coerce_span_attribute_value,
)
from bioetl.application.observability.span_helpers import traced_operation
from bioetl.domain.exceptions import BioETLError, MetricsServerError
from bioetl.domain.ports import ClockPort, MetricsPublisherPort, MetricsServerPort

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.ports import LoggerPort, TracingPort

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


class _MetricsTracingMixin:
    """Tracing attribute helpers for metrics administration flows."""

    TRACER_NAME = "bioetl.metrics_admin"

    def _build_span_attributes(
        self,
        *,
        operation: str,
        **extra: object,
    ) -> dict[str, object]:
        """Build bounded tracing attributes for operator metrics workflows."""
        return {
            "bioetl.component": "metrics_service",
            "bioetl.operation": operation,
            **extra,
        }

    @staticmethod
    def _set_result_attributes(
        span: Span,
        *,
        success: bool,
        error: str | None = None,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        """Attach bounded result attributes to the active metrics span."""
        span.set_attribute("bioetl.success", success)
        for key, value in (extra or {}).items():
            span.set_attribute(key, _coerce_span_attribute_value(value))
        if error is not None:
            span.set_attribute("error", True)
            span.set_attribute("bioetl.error", error)


class _MetricsStartMixin(_MetricsTracingMixin):
    """Metrics server start lifecycle helpers."""

    logger: LoggerPort
    _server: MetricsServerPort
    tracer: TracingPort | None
    clock: ClockPort
    _port: int | None
    _started_at: datetime | None

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
                extra={"bioetl.already_running": result.already_running},
            )
            return result

    def _start_impl(
        self,
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
                object.__setattr__(self, "_started_at", self.clock.now())
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

    _server: MetricsServerPort
    tracer: TracingPort | None
    _port: int | None
    _started_at: datetime | None

    def get_status(self) -> MetricsServerStatus:
        """Get the current status of the metrics server.

        Returns:
            MetricsServerStatus with current state.

        Example:
            >>> status = service.get_status()
            >>> if status.running:
            ...     logger.info("Server running", port=status.port)
        """
        if self.tracer is None:
            running = self._server.is_running()
            return MetricsServerStatus(
                running=running,
                port=self._port if running else None,
                started_at=self._started_at if running else None,
            )
        with traced_operation(
            self.tracer,
            "metrics.get_status",
            self._build_span_attributes(operation="get_status"),
            tracer_name=self.TRACER_NAME,
        ) as span:
            running = self._server.is_running()
            self._set_result_attributes(
                span,
                success=True,
                extra={"bioetl.running": running},
            )
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
        return bool(self._server.is_running())


class _MetricsGatewayMixin(_MetricsTracingMixin):
    """Gateway publication helpers for metrics administration flows."""

    logger: LoggerPort
    tracer: TracingPort | None
    _publisher: MetricsPublisherPort | None

    def push_to_gateway(
        self,
        *,
        gateway: str,
        run_label: str = "bioetl",
        grouping_key: dict[str, str] | None = None,
    ) -> PushResult:
        """Publish current metrics snapshot through the explicit publisher port."""
        labels = dict(grouping_key or {})
        if self.tracer is None:
            return self._push_to_gateway_impl(
                gateway=gateway,
                run_label=run_label,
                labels=labels,
            )
        with traced_operation(
            self.tracer,
            "metrics.push_to_gateway",
            self._build_span_attributes(
                operation="push_to_gateway",
                **{
                    "bioetl.run_label": run_label,
                    "bioetl.grouping_key_count": len(labels),
                },
            ),
            tracer_name=self.TRACER_NAME,
        ) as span:
            result = self._push_to_gateway_impl(
                gateway=gateway,
                run_label=run_label,
                labels=labels,
            )
            self._set_result_attributes(
                span, success=result.success, error=result.error
            )
            return result

    def _push_to_gateway_impl(
        self,
        *,
        gateway: str,
        run_label: str,
        labels: dict[str, str],
    ) -> PushResult:
        """Implement gateway publication without tracing concerns."""
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
    _port: int | None = field(default=None, repr=False)
    _started_at: datetime | None = field(default=None, repr=False)
