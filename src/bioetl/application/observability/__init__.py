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

__all__ = ["LifecyclePhase", "PipelineObserver"]
