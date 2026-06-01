"""Backward-compatible re-export for application-core span helpers."""

from __future__ import annotations

from bioetl.application.core import span_helpers as _public_span_helpers

_ClosableSpan = _public_span_helpers._ClosableSpan
_TracingProvider = _public_span_helpers._TracingProvider
build_pipeline_span_attributes = _public_span_helpers.build_pipeline_span_attributes
close_span = _public_span_helpers.close_span
close_span_with_shutdown = _public_span_helpers.close_span_with_shutdown
start_current_span = _public_span_helpers.start_current_span

__all__ = _public_span_helpers.__all__
