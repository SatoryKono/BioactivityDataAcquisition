"""Application layer observability components.

This package contains:
- PipelineObserver: Context manager for tracing execution lifecycle
- LifecyclePhase: Enum for pipeline lifecycle phases
- traced_operation: Async context manager for span management
- traced_sync_operation: Sync context manager for span management
- SpanBuilder: Builder pattern for consistent span attributes
- Observability utilities for the application layer

Architecture:
- Application layer defines WHAT to observe (Events)
- Infrastructure layer defines HOW to observe (Prometheus, Logs)

Unified Observability Pattern:
- All lifecycle events are emitted through PipelineObserver
- Services use emit_event() for structured logging with metrics
- Span helpers eliminate manual __enter__/__exit__ calls
- Single source of truth for all observability events
"""

from __future__ import annotations

from bioetl.application.observability.observer import LifecyclePhase, PipelineObserver
from bioetl.application.observability.span_context import (
    SpanBuilder,
    traced_operation,
    traced_sync_operation,
)

__all__ = [
    "LifecyclePhase",
    "PipelineObserver",
    "SpanBuilder",
    "traced_operation",
    "traced_sync_operation",
]
