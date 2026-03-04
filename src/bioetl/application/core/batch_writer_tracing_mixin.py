# mypy: disable-error-code=attr-defined
"""Tracing, lock-validation, and error-tracking helpers for BatchWriter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from bioetl.domain.locking import LockNotHeldError

if TYPE_CHECKING:
    from typing import Any as SpanType

    from bioetl.domain.types import BatchID


_WRITE_SPAN_ERRORS = (Exception,)


class BatchWriterTracingMixin:
    """Operational cross-cutting concerns for BatchWriter."""

    async def _validate_lock(self, operation: str) -> None:
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
        self, name: str, layer: str, record_count: int, batch_id: BatchID | None = None
    ) -> SpanType | None:
        """Start tracing span for write operation."""
        if not self._tracer:
            return None

        attrs: dict[
            str, Any  # Any: dynamic payload or structural mixin boundary
        ] = {  # Any: span attributes are heterogeneous by tracing contract
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

    def _end_span(self, span: SpanType | None, error: Exception | None = None) -> None:
        """Close tracing span with optional exception metadata."""
        if not span:
            return
        if error:
            span.set_attribute("error", True)
            span.record_exception(error)
        span.__exit__(None, None, None)

    def log_and_track_write_error(
        self, layer: str, error: Exception, batch_id: BatchID
    ) -> None:
        """Log write-layer error and track metrics."""
        error_type = self._error_classifier.classify(error)
        self._context.logger.error(
            "layer_write_failed",
            layer=layer,
            error=str(error),
            error_type=error_type.value,
            batch_id=str(batch_id),
        )
        self._batch_metrics.track_error(f"{layer}_write", error_type)


BatchWriterLockValidator = Callable[[], Awaitable[bool]] | None
