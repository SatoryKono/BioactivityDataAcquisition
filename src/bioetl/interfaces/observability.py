"""Observability interface for BioETL.

Re-exports observability components from the infrastructure layer.
This module provides a clean interface for external consumers.

Note:
    MetricsServerError and start_metrics_server are now imported from
    infrastructure.observability (not composition._bootstrap) to respect
    layer boundaries. Interfaces may import from infrastructure since
    exceptions are value objects.
"""

from __future__ import annotations

from bioetl.infrastructure.observability import (
    MetricsServerError,
    start_metrics_server,
)

__all__ = [
    "MetricsServerError",
    "start_metrics_server",
]
