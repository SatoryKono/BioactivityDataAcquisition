"""Backward-compatible re-export for application-core span helpers."""

from __future__ import annotations

from bioetl.application.core.span_helpers import (
    _ClosableSpan,
    _TracingProvider,
    build_pipeline_span_attributes,
    close_span,
    close_span_with_shutdown,
    start_current_span,
)

__all__ = [
    "_ClosableSpan",
    "_TracingProvider",
    "build_pipeline_span_attributes",
    "close_span",
    "close_span_with_shutdown",
    "start_current_span",
]
