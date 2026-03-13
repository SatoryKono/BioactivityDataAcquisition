"""Observability interface for BioETL.

Re-exports observability components for external consumers.

Note:
    MetricsServerError is defined in domain.exceptions (value object,
    can be imported by all layers). start_metrics_server is exposed via
    the composition facade so interfaces do not wire directly to bootstrap
    runtime internals or infrastructure.
"""

from __future__ import annotations

from bioetl.composition.entrypoints import start_metrics_server
from bioetl.domain.exceptions import MetricsServerError

__all__ = [
    "MetricsServerError",
    "start_metrics_server",
]
