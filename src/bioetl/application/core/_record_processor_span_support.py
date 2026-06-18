"""Span execution helpers for the legacy RecordProcessor."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast

from bioetl.application.core.batch_operation_errors import OPERATION_ERRORS
from bioetl.application.core.span_helpers import close_span
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.batch_transformer import (
        BatchTransformer,
        TransformResult,
    )
    from bioetl.application.core.span_helpers import _ClosableSpan
    from bioetl.domain.ports import TracingPort
    from bioetl.domain.types import BatchID

_PROCESSING_SPAN_ERRORS = OPERATION_ERRORS


class RecordProcessorSpanExecutor:
    """Wrap RecordProcessor stage coroutines with tracing span lifecycle."""

    def __init__(self, tracer: TracingPort) -> None:
        self._tracer = tracer

    async def execute_with_span(
        self,
        name: str,
        coro: Awaitable[object],
        batch_id: BatchID,
        count: int,
        on_error: Callable[[Exception], object] | None = None,
    ) -> object:
        """Execute coroutine with tracing span."""
        span = self._start_span(name, batch_id, count)
        try:
            result = await coro
            self._end_span(span)
            return result
        except _PROCESSING_SPAN_ERRORS as error:
            self._end_span(span, error)
            if on_error:
                on_error(error)
            raise

    async def execute_transform_with_span(
        self,
        *,
        transformer: BatchTransformer,
        records: list[JsonDict],
        batch_id: BatchID,
        start_index: int,
    ) -> TransformResult:
        """Execute transformation with extended span attributes."""
        span = self._start_span("transform", batch_id, len(records), input_count=True)
        try:
            result = await transformer.transform_batch(
                records,
                batch_id,
                start_index=start_index,
            )
            if span:
                span.set_attribute("bioetl.silver_count", len(result.silver_records))
                span.set_attribute("bioetl.gold_count", len(result.gold_records))
                span.set_attribute("bioetl.quarantined_count", result.quarantined_count)
            self._end_span(span)
            return result
        except _PROCESSING_SPAN_ERRORS as error:
            self._end_span(span, error)
            raise

    def _start_span(
        self,
        name: str,
        batch_id: BatchID,
        count: int,
        input_count: bool = False,
    ) -> Span | None:
        """Start a tracing span if tracer is available."""
        if not self._tracer:
            return None
        count_key = "bioetl.input_count" if input_count else "bioetl.record_count"
        attrs = {"bioetl.batch_id": str(batch_id), count_key: count}
        span = self._tracer.get_tracer("bioetl.processor").start_as_current_span(
            name,
            attributes=attrs,
        )
        typed_span = cast("Span", span)
        typed_span.__enter__()
        return typed_span

    def _end_span(self, span: Span | None, error: Exception | None = None) -> None:
        """End a tracing span."""
        close_span(cast("_ClosableSpan | None", span), error)
