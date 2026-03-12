"""Observability interface for BioETL.

Re-exports observability components for external consumers.

Note:
    MetricsServerError is defined in domain.exceptions (value object,
    can be imported by all layers). start_metrics_server is exposed via
    the composition runtime entrypoint so interfaces do not wire directly
    to infrastructure.
"""

from __future__ import annotations

from bioetl.composition.bootstrap.runtime.observability import start_metrics_server
from bioetl.domain.exceptions import MetricsServerError

__all__ = [
    "MetricsServerError",
    "start_metrics_server",
]
