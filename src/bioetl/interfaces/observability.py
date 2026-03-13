"""Observability interface for BioETL.

Re-exports observability components for external consumers.

Note:
    MetricsServerError is defined in domain.exceptions (value object,
    can be imported by all layers). start_metrics_server is exposed via
    the composition facade so interfaces do not wire directly to bootstrap
    runtime internals or infrastructure.
"""

from __future__ import annotations

from bioetl.domain.exceptions import MetricsServerError
from bioetl.domain.ports import LoggerPort

__all__ = [
    "MetricsServerError",
    "start_metrics_server",
]


def start_metrics_server(
    port: int = 8000,
    addr: str = "0.0.0.0",
    *,
    fail_fast: bool = False,
    retry_count: int = 3,
    retry_delay: float = 1.0,
    logger: LoggerPort | None = None,
) -> bool:
    """Start the metrics server through composition on demand."""
    from bioetl.composition.entrypoints import start_metrics_server as _impl

    return _impl(
        port=port,
        addr=addr,
        fail_fast=fail_fast,
        retry_count=retry_count,
        retry_delay=retry_delay,
        logger=logger,
    )
