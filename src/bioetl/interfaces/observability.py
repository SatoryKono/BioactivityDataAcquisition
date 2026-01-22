"""Observability interface for BioETL.

Re-exports observability components for external consumers.

Note:
    MetricsServerError is defined in domain.exceptions (value object,
    can be imported by all layers). start_metrics_server is re-exported
    from infrastructure.observability.
"""

from __future__ import annotations

from bioetl.domain.exceptions import MetricsServerError
from bioetl.infrastructure.observability import start_metrics_server

__all__ = [
    "MetricsServerError",
    "start_metrics_server",
]
