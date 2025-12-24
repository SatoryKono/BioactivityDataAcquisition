"""Infrastructure layer observability components.

This package contains implementations of observability ports:
- Metrics (Prometheus)
- Tracing (OpenTelemetry - optional)
- Logging (Structlog integration)
- Health Checks

Implements RULES.md §3 (Observability).
"""

from __future__ import annotations