"""Span helper utilities for unified tracing.

Provides context managers for tracing spans that properly handle
exceptions and ensure spans are always closed.

This module eliminates the need for manual __enter__/__exit__ calls
in application code (Phase 4 refactoring).

Usage:
    >>> async with traced_operation(tracer, "my_operation", {"key": "value"}) as span:
    ...     # Do work
    ...     span.set_attribute("result", "success")
"""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from bioetl.domain.ports import TracingPort


@contextmanager
def traced_operation(
    tracer: TracingPort,
    name: str,
    attributes: dict[str, Any] | None = None,
    tracer_name: str = "bioetl",
) -> Generator[Any, None, None]:
    """Context manager for synchronous tracing spans.

    Creates a span that is properly closed even if an exception occurs.
    Records exceptions on the span before re-raising.

    Args:
        tracer: TracingPort for creating spans
        name: Name of the span (e.g., "write_bronze", "transform_batch")
        attributes: Optional initial span attributes
        tracer_name: Name of the tracer (default: "bioetl")

    Yields:
        The span context for setting additional attributes

    Example:
        >>> with traced_operation(tracer, "write_bronze", {"layer": "bronze"}) as span:
        ...     # Write data
        ...     span.set_attribute("record_count", 100)

    """
    otel_tracer = tracer.get_tracer(tracer_name)
    span = otel_tracer.start_as_current_span(name, attributes=attributes or {})
    span.__enter__()

    try:
        yield span
    except Exception as e:
        span.set_attribute("error", True)
        span.set_attribute("error.type", type(e).__name__)
        span.record_exception(e)
        raise
    finally:
        span.__exit__(None, None, None)


@asynccontextmanager
async def traced_async_operation(
    tracer: TracingPort,
    name: str,
    attributes: dict[str, Any] | None = None,
    tracer_name: str = "bioetl",
) -> AsyncGenerator[Any, None]:
    """Async context manager for tracing spans.

    Creates a span that is properly closed even if an exception occurs.
    Records exceptions on the span before re-raising.

    Args:
        tracer: TracingPort for creating spans
        name: Name of the span (e.g., "write_bronze", "transform_batch")
        attributes: Optional initial span attributes
        tracer_name: Name of the tracer (default: "bioetl")

    Yields:
        The span context for setting additional attributes

    Example:
        >>> async with traced_async_operation(tracer, "fetch_data") as span:
        ...     data = await fetch()
        ...     span.set_attribute("record_count", len(data))

    """
    otel_tracer = tracer.get_tracer(tracer_name)
    span = otel_tracer.start_as_current_span(name, attributes=attributes or {})
    span.__enter__()

    try:
        yield span
    except Exception as e:
        span.set_attribute("error", True)
        span.set_attribute("error.type", type(e).__name__)
        span.record_exception(e)
        raise
    finally:
        span.__exit__(None, None, None)
