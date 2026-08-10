"""Lifecycle runner for bounded control-plane metric refreshes."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Protocol

from bioetl.domain.exceptions import BioETLError

CONTROL_PLANE_METRICS_REFRESH_INTERVAL_SECONDS = 60.0
_REFRESH_ERRORS = (BioETLError, OSError, RuntimeError, TypeError, ValueError)


class ControlPlaneMetricsRefresher(Protocol):
    """Synchronous bounded refresh seam owned by composition."""

    def refresh(self) -> object:
        """Refresh aggregate metrics without serving an HTTP scrape."""
        ...


async def refresh_control_plane_metrics(
    refresher: ControlPlaneMetricsRefresher,
) -> bool:
    """Run one refresh off-loop and contain typed source failures."""
    try:
        _ = await asyncio.to_thread(refresher.refresh)
    except _REFRESH_ERRORS:
        return False
    return True


async def run_periodic_control_plane_metrics_refresh(
    refresher: ControlPlaneMetricsRefresher,
    *,
    interval_seconds: float,
) -> None:
    """Refresh after every interval until the owning task is cancelled."""
    while True:
        await asyncio.sleep(interval_seconds)
        _ = await refresh_control_plane_metrics(refresher)


async def stop_control_plane_metrics_refresh(task: asyncio.Task[None] | None) -> None:
    """Cancel and join the optional periodic refresh task."""
    if task is None:
        return
    _ = task.cancel()
    with suppress(asyncio.CancelledError):
        await task


__all__ = [
    "CONTROL_PLANE_METRICS_REFRESH_INTERVAL_SECONDS",
    "ControlPlaneMetricsRefresher",
    "refresh_control_plane_metrics",
    "run_periodic_control_plane_metrics_refresh",
    "stop_control_plane_metrics_refresh",
]
