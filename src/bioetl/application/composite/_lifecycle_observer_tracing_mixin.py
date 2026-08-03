"""Composite lifecycle tracing facade composed from focused helpers."""

from __future__ import annotations

from bioetl.application.composite._lifecycle_observer_tracing_helpers import (
    CompositeLifecycleEventMetricsMixin,
    CompositeLifecycleSpanManagementMixin,
)


class CompositeLifecycleTracingMixin(
    CompositeLifecycleEventMetricsMixin,
    CompositeLifecycleSpanManagementMixin,
):
    """Tracing facade composed from focused event and span helpers."""
