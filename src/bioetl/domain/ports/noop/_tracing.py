"""No-op tracing implementation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from types import TracebackType


class _NoOpSpan:
    """No-op span that mirrors OpenTelemetry ``Span`` interface."""

    def __enter__(self) -> Self:
        """Enter the span context manager and return self."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the span context manager — no-op, does not suppress exceptions.

        Args:
            exc_type: Exception type if an error occurred, otherwise None.
            exc_val: Exception instance if an error occurred, otherwise None.
            exc_tb: Traceback if an error occurred, otherwise None.
        """
        return None

    def set_attribute(
        self,
        key: str,
        value: object,
    ) -> None:
        """No-op implementation — discards the span attribute.

        Args:
            key: Attribute name (ignored).
            value: Attribute value (ignored).
        """
        _ = key, value
        return None

    def set_status(self, _status: object) -> None:
        """No-op implementation — discards the span status.

        Args:
            _status: Status object (ignored).
        """
        return None

    def add_event(
        self,
        name: str,
        attributes: Mapping[str, object] | None = None,
    ) -> None:
        """No-op implementation — discards span events.

        Args:
            name: Event name (ignored).
            attributes: Optional event attributes (ignored).
        """
        _ = name, attributes
        return None

    def record_exception(self, exception: BaseException) -> None:
        """No-op implementation — discards the recorded exception.

        Args:
            exception: Exception to record (ignored).
        """
        _ = exception
        return None


class _NoOpOtelTracer:
    """No-op tracer that mirrors OpenTelemetry ``Tracer`` interface."""

    def start_as_current_span(
        self,
        *_args: Any,  # Any: OTel signature is intentionally flexible
        **_kwargs: Any,  # Any: OTel signature is intentionally flexible
    ) -> _NoOpSpan:
        """Return a no-op span without starting any real tracing context.

        Args:
            *_args: Positional arguments matching the OTel Tracer API (ignored).
            **_kwargs: Keyword arguments matching the OTel Tracer API (ignored).

        Returns:
            A new no-op span instance.
        """
        return _NoOpSpan()


class NoOpTracing:
    """No-op implementation of TracingPort (Null Object pattern)."""

    is_noop = True

    def get_tracer(self, name: str) -> _NoOpOtelTracer:
        """Return a no-op OTel-compatible tracer.

        Args:
            name: Tracer name (ignored).

        Returns:
            A new no-op tracer instance.
        """
        del name
        return _NoOpOtelTracer()

    def close(self) -> None:
        """No-op implementation — no spans to flush or resources to release."""
        return None

    def flush(self) -> None:
        """No-op implementation — no spans to flush."""
        return None
