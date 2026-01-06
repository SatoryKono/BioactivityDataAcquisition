"""No-op implementation of TracingPort."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from types import TracebackType


class NoOpTracer:
    """No-op tracer that does nothing."""

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit."""

    def start_as_current_span(self, *args: Any, **kwargs: Any) -> Self:
        """Start a new span (no-op).

        Accepts any arguments to be compatible with OpenTelemetry tracer.
        """
        return self

    def set_attribute(self, key: str, value: Any) -> None:
        """Set span attribute (no-op)."""

    def set_status(self, status: Any) -> None:
        """Set span status (no-op)."""

    def record_exception(self, exception: Exception) -> None:
        """Record exception (no-op)."""


class NoOpTracing:
    """No-op implementation of TracingPort.

    Unified implementation for when distributed tracing is disabled.
    Used as the single source of truth for no-op tracing.
    """

    def __init__(self) -> None:
        """Initialize no-op tracing."""
        self._closed = False

    def get_tracer(self, name: str) -> NoOpTracer:
        """Get a no-op tracer."""
        return NoOpTracer()

    def close(self) -> None:
        """No-op close. Idempotent."""
        self._closed = True
