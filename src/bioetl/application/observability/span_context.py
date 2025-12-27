"""Span context manager for unified tracing operations.

Provides a consistent way to manage OpenTelemetry spans across the application,
eliminating manual __enter__/__exit__ calls and ensuring proper error handling.

Usage:
    >>> async with traced_operation(tracer, "transform_batch", batch_id=bid):
    ...     result = await transform(batch)

    # Sync context manager also available:
    >>> with traced_sync_operation(tracer, "validate_schema", table=name):
    ...     validate(schema)
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager, contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from bioetl.domain.ports import TracingPort


@asynccontextmanager
async def traced_operation(
    tracer: TracingPort | None,
    operation_name: str,
    tracer_name: str = "bioetl",
    **attributes: Any,
) -> AsyncIterator[Any]:
    """Async context manager for traced operations.

    Creates an OpenTelemetry span for the operation if tracer is available.
    Automatically records exceptions and sets error attributes.

    Args:
        tracer: Optional TracingPort. If None, yields None without tracing.
        operation_name: Name of the span (e.g., "transform_batch", "write_silver").
        tracer_name: Tracer name for grouping (default: "bioetl").
        **attributes: Additional span attributes to set on creation.

    Yields:
        The span object if tracer is available, None otherwise.

    Example:
        >>> async with traced_operation(tracer, "process_batch", batch_id=bid):
        ...     await process(records)

        >>> async with traced_operation(None, "no_trace"):  # Safe no-op
        ...     await do_work()

    Notes:
        - Safe to use with None tracer (no-op behavior)
        - Automatically records exceptions with traceback
        - Sets "error" attribute to True on exception
        - Records operation duration as span attribute
    """
    if tracer is None:
        yield None
        return

    otel_tracer = tracer.get_tracer(tracer_name)

    # Prepare attributes with bioetl. prefix
    span_attrs = {f"bioetl.{k}": str(v) for k, v in attributes.items()}

    span = otel_tracer.start_as_current_span(operation_name, attributes=span_attrs)
    start_time = time.monotonic()

    with span:
        try:
            yield span
        except Exception as exc:
            # Record exception details on span
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(exc).__name__)
            span.set_attribute("error.message", str(exc))
            span.record_exception(exc)
            raise
        finally:
            # Record duration
            duration_ms = (time.monotonic() - start_time) * 1000
            span.set_attribute("bioetl.duration_ms", duration_ms)


@contextmanager
def traced_sync_operation(
    tracer: TracingPort | None,
    operation_name: str,
    tracer_name: str = "bioetl",
    **attributes: Any,
) -> Iterator[Any]:
    """Sync context manager for traced operations.

    Same as traced_operation but for synchronous code.

    Args:
        tracer: Optional TracingPort. If None, yields None without tracing.
        operation_name: Name of the span.
        tracer_name: Tracer name for grouping (default: "bioetl").
        **attributes: Additional span attributes.

    Yields:
        The span object if tracer is available, None otherwise.

    Example:
        >>> with traced_sync_operation(tracer, "validate_config"):
        ...     validate(config)
    """
    if tracer is None:
        yield None
        return

    otel_tracer = tracer.get_tracer(tracer_name)

    # Prepare attributes with bioetl. prefix
    span_attrs = {f"bioetl.{k}": str(v) for k, v in attributes.items()}

    span = otel_tracer.start_as_current_span(operation_name, attributes=span_attrs)
    start_time = time.monotonic()

    with span:
        try:
            yield span
        except Exception as exc:
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(exc).__name__)
            span.set_attribute("error.message", str(exc))
            span.record_exception(exc)
            raise
        finally:
            duration_ms = (time.monotonic() - start_time) * 1000
            span.set_attribute("bioetl.duration_ms", duration_ms)


class SpanBuilder:
    """Builder for creating traced operations with consistent attributes.

    Useful when the same attributes need to be applied to multiple spans.

    Example:
        >>> builder = SpanBuilder(tracer, "bioetl.executor")
        >>> builder = builder.with_attrs(pipeline="chembl", run_id=rid)
        >>> async with builder.span("fetch_batch"):
        ...     await fetch()
        >>> async with builder.span("transform_batch"):
        ...     await transform()
    """

    def __init__(
        self,
        tracer: TracingPort | None,
        tracer_name: str = "bioetl",
    ) -> None:
        """Initialize span builder.

        Args:
            tracer: Optional TracingPort.
            tracer_name: Tracer name for all spans created by this builder.
        """
        self._tracer = tracer
        self._tracer_name = tracer_name
        self._base_attrs: dict[str, Any] = {}

    def with_attrs(self, **attrs: Any) -> SpanBuilder:
        """Add base attributes to be included in all spans.

        Returns a new SpanBuilder instance with the additional attributes.

        Args:
            **attrs: Attributes to add.

        Returns:
            New SpanBuilder with combined attributes.
        """
        new_builder = SpanBuilder(self._tracer, self._tracer_name)
        new_builder._base_attrs = {**self._base_attrs, **attrs}
        return new_builder

    @asynccontextmanager
    async def span(
        self,
        operation_name: str,
        **extra_attrs: Any,
    ) -> AsyncIterator[Any]:
        """Create a traced operation with builder's attributes.

        Args:
            operation_name: Name of the span.
            **extra_attrs: Additional attributes for this specific span.

        Yields:
            The span object if tracer is available, None otherwise.
        """
        combined_attrs = {**self._base_attrs, **extra_attrs}
        async with traced_operation(
            self._tracer,
            operation_name,
            self._tracer_name,
            **combined_attrs,
        ) as span:
            yield span

    @contextmanager
    def sync_span(
        self,
        operation_name: str,
        **extra_attrs: Any,
    ) -> Iterator[Any]:
        """Create a sync traced operation with builder's attributes.

        Args:
            operation_name: Name of the span.
            **extra_attrs: Additional attributes for this specific span.

        Yields:
            The span object if tracer is available, None otherwise.
        """
        combined_attrs = {**self._base_attrs, **extra_attrs}
        with traced_sync_operation(
            self._tracer,
            operation_name,
            self._tracer_name,
            **combined_attrs,
        ) as span:
            yield span
