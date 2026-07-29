"""Pipeline span lifecycle helpers owned by application.core."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from types import TracebackType
from typing import TYPE_CHECKING, Protocol, cast

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext

__all__ = [
    "_ClosableSpan",
    "_TracingProvider",
    "build_pipeline_span_attributes",
    "close_span",
    "close_span_with_shutdown",
    "start_current_span",
]


class _CurrentSpanStarter(Protocol):
    """Minimal tracer contract for starting current spans."""

    def start_as_current_span(
        self,
        name: str,
        *,
        attributes: dict[str, object],
    ) -> object: ...


class _TracingProvider(Protocol):
    """Minimal tracing-provider contract used by internal helpers."""

    def get_tracer(self, name: str) -> _CurrentSpanStarter: ...


class _ClosableSpan(Protocol):
    """Minimal tracing span contract used by internal helpers."""

    def set_attribute(self, key: str, value: object) -> None: ...
    def record_exception(self, error: BaseException) -> None: ...
    def __enter__(self) -> _ClosableSpan: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> object: ...


def build_pipeline_span_attributes(
    *,
    config: PipelineConfig,
    runtime: RuntimeConfig,
    context: PipelineContext | None = None,
) -> dict[str, object]:
    """Build the shared BioETL pipeline span attribute set."""
    attributes: dict[str, object] = {
        "bioetl.pipeline": config.pipeline_name or "unknown",
        "bioetl.provider": config.provider,
        "bioetl.entity_type": config.entity_type,
        "bioetl.run_type": runtime.run_type.value,
    }
    if context is not None:
        attributes["bioetl.run_id"] = str(context.run_id)
    return attributes


@contextmanager
def start_current_span(
    *,
    tracing: _TracingProvider,
    tracer_name: str,
    span_name: str,
    attributes: dict[str, object],
) -> Generator[Span, None, None]:
    """Start and yield a current tracing span with explicit attributes."""
    otel_tracer = tracing.get_tracer(tracer_name)
    with cast(
        "Span",
        otel_tracer.start_as_current_span(span_name, attributes=attributes),
    ) as span:
        yield span


def close_span(span: _ClosableSpan | None, error: Exception | None = None) -> None:
    """Close a tracing span and optionally record an exception."""
    if not span:
        return
    if error:
        span.set_attribute("error", True)
        span.record_exception(error)
    span.__exit__(None, None, None)


def close_span_with_shutdown(span: _ClosableSpan | None) -> None:
    """Close a tracing span after marking shutdown state."""
    if not span:
        return
    span.set_attribute("bioetl.shutdown", True)
    span.__exit__(None, None, None)
