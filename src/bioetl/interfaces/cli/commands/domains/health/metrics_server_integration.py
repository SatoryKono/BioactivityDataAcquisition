"""Metrics server integration for CLI commands.

Provides utilities for starting the Prometheus metrics HTTP server
alongside pipeline operations. The metrics server exposes Prometheus-compatible
metrics endpoint while pipelines execute.

This module follows the thin controller pattern - it delegates to
composition layer for server startup, keeping side-effects out of bootstrap.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

__all__ = [
    "ensure_metrics_server_started",
    "metrics_server_context",
]


def ensure_metrics_server_started() -> bool:
    """Start the metrics server through composition on demand."""
    from bioetl.composition.execution_service_access import (
        ensure_metrics_server_started as _impl,
    )

    return bool(_impl())


@contextmanager
def metrics_server_context() -> Iterator[bool]:
    """Context manager that ensures metrics server is started.

    Starts the Prometheus metrics HTTP server before yielding.
    The server runs as a daemon thread and doesn't need explicit shutdown.

    Yields:
        True if server was started, False if disabled.

    Example:
        with metrics_server_context():
            # Metrics server is running
            await run_pipeline()
        # Server continues running (daemon thread)

    Returns:
        Iterator over results.
    """
    # Re-exported from entrypoints, use directly
    started = ensure_metrics_server_started()
    yield started


COMMANDS = (metrics_server_context,)
