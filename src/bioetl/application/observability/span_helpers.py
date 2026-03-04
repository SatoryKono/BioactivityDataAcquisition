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

__all__ = ["traced_async_operation"]


import sys
from contextlib import asynccontextmanager, contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from bioetl.domain.ports import TracingPort


@contextmanager
def _span_context(
    tracer: TracingPort,
    name: str,
    attributes: dict[str, Any]  # Any: OTel span attributes are heterogeneous
    | None = None,  # Any: OTel span attributes are heterogeneous
    tracer_name: str = "bioetl",
) -> Generator[Any, None, None]:  # Any: OTel span context manager yield type
    """Internal helper to manage span lifecycle."""
    otel_tracer = tracer.get_tracer(tracer_name)
    span = otel_tracer.start_as_current_span(name, attributes=attributes or {})
    span.__enter__()

    try:
        yield span
    finally:
        exc_type, exc, exc_tb = sys.exc_info()
        if exc is not None:
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(exc).__name__)
            if isinstance(exc, Exception):
                span.record_exception(exc)
        # Keep closing semantics stable for existing OTel facade tests.
        span.__exit__(None, None, None)


traced_operation = _span_context


@asynccontextmanager
async def traced_async_operation(
    tracer: TracingPort,
    name: str,
    attributes: dict[str, Any]  # Any: OTel span attributes are heterogeneous
    | None = None,  # Any: OTel span attributes are heterogeneous
    tracer_name: str = "bioetl",
) -> AsyncGenerator[Any, None]:  # Any: OTel span context manager yield type
    """Async context manager for tracing spans.

    Args:
        tracer: Tracing instance.
        name: Identifier name.
        attributes: Attributes.
        tracer_name: Name of the tracer.

    Returns:
        Iterator over results.
    """
    with _span_context(tracer, name, attributes, tracer_name) as span:
        yield span
