"""Observability interface for BioETL.

Re-exports observability components from the composition layer.
This module exists for backward compatibility and provides a clean
interface for external consumers.

Note:
    For architectural purity, these components are managed by the
    composition layer and re-exported here for the interfaces layer.
"""

from __future__ import annotations

from bioetl.composition._bootstrap import (
    MetricsServerError,
    start_metrics_server,
)

__all__ = [
    "MetricsServerError",
    "start_metrics_server",
]
