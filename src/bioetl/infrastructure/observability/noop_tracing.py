"""No-op implementation of TracingPort."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from types import TracebackType


class NoOpTracer:
    """No-op tracer that does nothing."""

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass

    def start_as_current_span(self, name: str) -> Self:
        return self

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, status: Any) -> None:
        pass

    def record_exception(self, exception: Exception) -> None:
        pass


class NoOpTracing:
    """No-op implementation of TracingPort."""

    def get_tracer(self, name: str) -> NoOpTracer:
        return NoOpTracer()
