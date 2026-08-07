"""Tracing protocol port (OTel-compatible facade)."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, runtime_checkable


@runtime_checkable
class SpanHandle(Protocol):
    """Minimal context-managed span surface required by BioETL callers."""

    def __enter__(self) -> SpanHandle: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool | None: ...

    def set_attribute(self, key: str, value: object) -> None: ...

    def add_event(
        self, name: str, attributes: dict[str, object] | None = None
    ) -> None: ...

    def record_exception(self, exception: BaseException) -> None: ...


@runtime_checkable
class TracerHandle(Protocol):
    """Minimal tracer surface returned by TracingPort.get_tracer."""

    def start_as_current_span(
        self,
        name: str,
        *,
        attributes: dict[str, object] | None = None,
    ) -> SpanHandle: ...


@runtime_checkable
class TracingPort(Protocol):
    """Port for distributed tracing."""

    def get_tracer(
        self,
        name: str,
    ) -> TracerHandle:
        """Return OpenTelemetry-compatible tracer instance.

        Args:
            name: Tracer name, typically the instrumented module or component name.

        Returns:
            Tracer handle that yields context-managed span handles exposing
            ``set_attribute()``, ``add_event()``, and ``record_exception()`` so
            NoOp and concrete adapters remain behaviorally interchangeable.
        """
        ...

    def close(self) -> None:
        """Flush pending spans and cleanup resources."""
        ...

    def flush(self) -> None:
        """Best-effort flush of pending spans without shutting the provider down."""
        ...
