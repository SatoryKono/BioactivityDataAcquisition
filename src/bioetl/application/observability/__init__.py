"""Application layer observability components.

This package contains:
- PipelineObserver: Context manager for tracing execution lifecycle
- Observability utilities for the application layer

Architecture:
- Application layer defines WHAT to observe (Events)
- Infrastructure layer defines HOW to observe (Prometheus, Logs)
"""

from __future__ import annotations