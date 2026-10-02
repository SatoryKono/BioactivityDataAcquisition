"""Tracing, lock-validation, and error-tracking helpers for BatchWriter."""

from __future__ import annotations

import traceback
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Protocol

from bioetl.application.core.batch_tracing import close_span
from bioetl.domain.locking import LockNotHeldError
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from typing import Any as SpanType

    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.ports import TracingPort
    from bioetl.domain.types import BatchID

_WRITE_SPAN_ERRORS = (Exception,)


class _BatchWriterTracingHostProtocol(Protocol):
    """Internal dependencies initialized by BatchWriter's constructor."""

    _lock_validator: Callable[[], Awaitable[bool]] | None
    _provider: str
    _entity_type: str
    _context: PipelineContext
    _tracer: TracingPort | None
    _error_classifier: ErrorClassifier
    _batch_metrics: BatchMetricsRecorderService


class BatchWriterTracingMixin:
    """Operational cross-cutting concerns for BatchWriter."""

    async def _validate_lock(
        self: _BatchWriterTracingHostProtocol, operation: str
    ) -> None:
        """Validate lock ownership before write operation."""
        lock_validator = self._lock_validator
        if lock_validator is None:
            return
        if not await lock_validator():
            table_name = f"{self._provider}_{self._entity_type}"
            self._context.logger.error(
                "Lock lost before write",
                operation=operation,
                table=table_name,
                run_id=str(self._context.run_id),
            )
            raise LockNotHeldError(operation, f"lock:{table_name}")

    def _start_span(
        self: _BatchWriterTracingHostProtocol,
        name: str,
        layer: str,
        record_count: int,
        batch_id: BatchID | None = None,
    ) -> SpanType | None:
        """Start tracing span for write operation."""
        if not self._tracer:
            return None
        attrs: JsonDict = {
            "bioetl.layer": layer,
            "bioetl.record_count": record_count,
            "bioetl.provider": self._provider,
            "bioetl.entity_type": self._entity_type,
        }
        if batch_id:
            attrs["bioetl.batch_id"] = str(batch_id)
        span = self._tracer.get_tracer("bioetl.batch_writer").start_as_current_span(
            name, attributes=attrs
        )
        span.__enter__()
        return span

    def _end_span(
        self: _BatchWriterTracingHostProtocol,
        span: SpanType | None,
        error: Exception | None = None,
    ) -> None:
        """Close tracing span with optional exception metadata."""
        close_span(span, error)

    def log_and_track_write_error(
        self: _BatchWriterTracingHostProtocol,
        layer: str,
        error: Exception,
        batch_id: BatchID,
        *,
        record_count: int = 0,
    ) -> None:
        """Log write-layer error and track metrics.
        Args:
            layer: Medallion layer name where the error occurred (e.g., ``'silver'``).
            error: Exception that caused the write failure.
            batch_id: Batch identifier for correlation in log output.
        """
        error_type = self._error_classifier.classify(error)
        error_message = str(error) or repr(error)
        self._context.logger.error(
            "layer_write_failed",
            layer=layer,
            error=error_message,
            error_type=error_type.value,
            exception_type=type(error).__name__,
            exception_module=type(error).__module__,
            traceback="".join(
                traceback.format_exception(
                    type(error),
                    error,
                    error.__traceback__,
                )
            ).strip(),
            batch_id=str(batch_id),
            exc_info=True,
        )
        self._batch_metrics.track_error(f"{layer}_write", error_type)
        self._batch_metrics.track_batch_failed(stage=layer, count=record_count)


BatchWriterLockValidator = Callable[[], Awaitable[bool]] | None
