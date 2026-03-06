"""No-op tracing implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from types import TracebackType


class _NoOpSpan:
    """No-op span that mirrors OpenTelemetry ``Span`` interface."""

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return None

    def set_attribute(
        self,
        _key: str,
        _value: object,
    ) -> None:
        return None

    def set_status(self, _status: object) -> None:
        return None

    def record_exception(self, _exception: Exception) -> None:
        return None


class _NoOpOtelTracer:
    """No-op tracer that mirrors OpenTelemetry ``Tracer`` interface."""

    def start_as_current_span(
        self,
        *_args: Any,  # Any: OTel signature is intentionally flexible
        **_kwargs: Any,  # Any: OTel signature is intentionally flexible
    ) -> _NoOpSpan:
        return _NoOpSpan()


class NoOpTracing:
    """No-op implementation of TracingPort (Null Object pattern)."""

    def get_tracer(self, _name: str) -> _NoOpOtelTracer:
        return _NoOpOtelTracer()

    def close(self) -> None:
        return None
