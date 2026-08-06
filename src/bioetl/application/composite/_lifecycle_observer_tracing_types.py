"""Shared types for composite lifecycle tracing helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort

if TYPE_CHECKING:
    from types import TracebackType

_PIPELINE_TRACE_NAMESPACE = "bioetl.pipeline"


class _CompositeSpanHandleProtocol(Protocol):
    """Minimal span handle surface used by composite lifecycle tracing."""

    def __enter__(self) -> object: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> object | None: ...

    def set_attribute(self, key: str, value: object) -> None: ...

    def record_exception(self, exception: BaseException) -> None: ...


class _CompositeLifecycleTracingHost(Protocol):
    """Structural contract required by composite lifecycle tracing helpers."""

    logger: LoggerPort
    metrics: MetricsPort | None
    tracer: TracingPort | None
    _run_start_times: dict[str, float]
    _phase_start_times: dict[tuple[str, str], float]
    _run_spans: dict[str, _CompositeSpanHandleProtocol]
    _phase_spans: dict[tuple[str, str], _CompositeSpanHandleProtocol]

    @staticmethod
    def _normalize_severity(level: str) -> str: ...

    @staticmethod
    def _pipeline_name(composite_name: str) -> str: ...

    def _build_run_trace_attributes(
        self,
        *,
        composite_name: str,
        run_id: str,
    ) -> dict[str, object]: ...

    def _has_real_tracing(self) -> bool: ...

    def _build_phase_trace_attributes(
        self,
        *,
        composite_name: str,
        run_id: str,
        phase_name: str,
    ) -> dict[str, object]: ...

    def _close_span_safely(
        self,
        span: _CompositeSpanHandleProtocol | None,
        *,
        status: str,
        duration_seconds: float | None,
        error: Exception | None = None,
        flush_tracer: bool = False,
    ) -> None: ...

    def _close_phase_span(
        self,
        *,
        run_id: str,
        phase_name: str,
        status: str,
        duration_seconds: float | None,
        error: Exception | None = None,
    ) -> None: ...


__all__ = [
    "_PIPELINE_TRACE_NAMESPACE",
    "_CompositeLifecycleTracingHost",
    "_CompositeSpanHandleProtocol",
]
