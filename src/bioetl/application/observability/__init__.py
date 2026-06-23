"""Application layer observability components.

This package contains:
- PipelineObserver: Context manager for tracing execution lifecycle
- LifecyclePhase: Enum for pipeline lifecycle phases
- Observability utilities for the application layer

Architecture:
- Application layer defines WHAT to observe (Events)
- Infrastructure layer defines HOW to observe (Prometheus, Logs)

Unified Observability Pattern:
- All lifecycle events are emitted through PipelineObserver
- Services use emit_event() for structured logging with metrics
- Single source of truth for all observability events
"""

from __future__ import annotations

from bioetl.application.observability.observer import LifecyclePhase, PipelineObserver
from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.application.observability.span_helpers import (
    traced_async_operation,
    traced_operation,
)

__all__ = [
    "LifecyclePhase",
    "PipelineMetricsRecorder",
    "PipelineObserver",
    "traced_async_operation",
    "traced_operation",
]
