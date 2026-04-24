"""Observability helpers for HTTP retry orchestration."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, NoReturn, Protocol, cast

from bioetl.domain.exceptions import CircuitBreakerOpenError, RetryExhaustedError
from bioetl.domain.ports import LoggerPort, TracingPort
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from collections.abc import Callable


class SpanLike(Protocol):
    """Minimal span contract used by retry observability flow."""

    def __enter__(self) -> SpanLike: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> object | None: ...

    def set_attribute(self, key: str, value: object) -> None:
        """Attach one structured attribute to the active span."""
        ...

    def record_exception(self, exception: Exception) -> None:
        """Attach one exception event to the active span."""
        ...


class _NoOpSpan:
    """Best-effort span used when tracing is intentionally disabled upstream."""

    def __enter__(self) -> _NoOpSpan:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> object | None:
        return None

    def set_attribute(self, key: str, value: object) -> None:
        _ = (key, value)

    def add_event(self, name: str, attributes: object | None = None) -> None:
        _ = (name, attributes)

    def record_exception(self, exception: Exception) -> None:
        _ = exception


class _OtelTracerLike(Protocol):
    """Minimal tracer contract returned by TracingPort.get_tracer()."""

    def start_as_current_span(
        self,
        name: str,
        *,
        attributes: dict[str, object],
    ) -> SpanLike: ...


class RetryStateLike(Protocol):
    """Minimal retry-state contract used by retry observability helpers."""

    retries: int
    status_code: int
    attempts_made: int
    last_error: Exception | None


def start_request_span(
    tracer: TracingPort | None,
    *,
    provider: str,
    run_id: RunID | None,
    method: str,
    url: str,
) -> SpanLike:
    """Create and enter the request span for retry orchestration."""
    if tracer is None:
        noop_span = _NoOpSpan()
        noop_span.__enter__()
        return noop_span
    otel_tracer = cast(_OtelTracerLike, tracer.get_tracer("bioetl.http"))
    span: SpanLike = otel_tracer.start_as_current_span(
        f"http.{method.lower()}",
        attributes={
            "http.method": method,
            "http.url": url,
            "bioetl.provider": provider,
            "bioetl.run_id": str(run_id) if run_id else "unknown",
        },
    )
    span.__enter__()
    return span


def mark_span_error(
    span: SpanLike,
    error_type: str,
    exc: Exception | None = None,
) -> None:
    """Mark span as failed and optionally record the triggering exception."""
    span.set_attribute("error", True)
    span.set_attribute("error.type", error_type)
    if exc is not None:
        span.record_exception(exc)


def finalize_request_observability(
    span: SpanLike,
    retry_state: RetryStateLike,
    *,
    method: str,
    start_time: float,
    record_metrics: Callable[[str, float, int, int, Exception | None], None],
) -> None:
    """Finalize span and metrics for a completed request lifecycle."""
    duration = time.perf_counter() - start_time
    retries = retry_state.retries
    status_code = retry_state.status_code
    last_error = retry_state.last_error
    span.set_attribute("http.retries", retries)
    span.set_attribute("bioetl.duration_ms", duration * 1000)
    span.__exit__(None, None, None)
    record_metrics(method, duration, status_code, retries, last_error)


def raise_retry_exhausted(
    url: str,
    retry_state: RetryStateLike,
    span: SpanLike,
) -> NoReturn:
    """Raise the terminal retry exhaustion error after span bookkeeping."""
    last_error = retry_state.last_error
    attempts_made = retry_state.attempts_made
    mark_span_error(span, "retry_exhausted", last_error)
    raise RetryExhaustedError(url, attempts_made, last_error)


def handle_circuit_breaker_trip(
    exc: CircuitBreakerOpenError,
    *,
    method: str,
    url: str,
    span: SpanLike,
    provider: str,
    logger: LoggerPort | None,
) -> None:
    """Record circuit-breaker open state without altering propagation semantics."""
    mark_span_error(span, "circuit_breaker_open", exc)
    if logger:
        logger.warning(
            "http_circuit_breaker_open",
            url=url,
            method=method,
            provider=provider,
            retry_after=exc.retry_after,
        )
