"""In-memory snapshot of the default Run Explorer recent-launch page.

The background scan owns catalog and report-index reads. A default browse
request recomputes event ages from the request clock and does not start a
second full index scan while a snapshot is already published.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any, Protocol, cast

from bioetl.application.runtime_clock import current_utc_time
from bioetl.domain.ports import RunManifestPort
from bioetl.interfaces.http.recent_pipeline_runs import (
    RECENT_TIMING_FIELDS,
    _scope,
    list_recent_pipeline_runs,
    refresh_recent_timing,
)
from bioetl.interfaces.http.run_report_ops import _concrete_run_id

DEFAULT_RECENT_LIMIT = 10
RUN_EXPLORER_SNAPSHOT_INTERVAL_SECONDS = 1.0
_REFRESH_ERRORS = (OSError, RuntimeError, TypeError, ValueError, KeyError)


class _SnapshotSource(Protocol):
    @property
    def _run_manifest_port(self) -> RunManifestPort | None: ...

    @property
    def _run_ledger_port(self) -> object | None: ...


class RunExplorerSnapshotCache:
    """Last successful default browse payload, without frozen event ages."""

    def __init__(self) -> None:
        self._stored: dict[str, object] | None = None

    def materialize(self, *, now: datetime | None = None) -> dict[str, object] | None:
        """Copy the stored page and measure ages at ``now``."""
        stored = self._stored
        if stored is None:
            return None
        payload = dict(stored)
        items = payload.get("items")
        if payload.get("order_by") != "started_at_desc" or not isinstance(items, list):
            return payload
        observed = now if now is not None else current_utc_time()
        payload["items"] = [
            refresh_recent_timing(item, now=observed)
            if isinstance(item, dict)
            else item
            for item in items
        ]
        return payload

    async def refresh_once(self, source: _SnapshotSource) -> None:
        """Replace the snapshot from one catalog scan, keeping the last good page."""
        manifest_port = source._run_manifest_port
        if manifest_port is None:
            return
        try:
            payload = await asyncio.to_thread(
                list_recent_pipeline_runs,
                pipeline=".*",
                workflow=".*",
                run_type=".*",
                selected_run_id="-",
                lookup_run_id=None,
                limit=DEFAULT_RECENT_LIMIT,
                manifest_port=manifest_port,
                ledger_port=cast(Any, source._run_ledger_port),
            )
        except _REFRESH_ERRORS:
            return
        self._stored = _without_timing(payload)


def is_default_recent_browse(
    *,
    view: str | None,
    limit: int,
    pipeline: str | None,
    workflow: str | None,
    run_type: str | None,
    run_id: str | None,
    lookup_run_id: str | None,
) -> bool:
    """Return True for the shipped All / All / All, run_id=- , limit=10 browse."""
    if view != "recent" or limit != DEFAULT_RECENT_LIMIT:
        return False
    if _concrete_run_id(run_id) is not None or (lookup_run_id or "").strip():
        return False
    return not (_scope(pipeline) or _scope(workflow) or _scope(run_type))


def take_default_recent_snapshot(
    cache: object,
    *,
    view: str | None,
    limit: int,
    pipeline: str | None,
    workflow: str | None,
    run_type: str | None,
    run_id: str | None,
    lookup_run_id: str | None,
) -> dict[str, object] | None:
    """Return a request-timed page when ``cache`` already holds the default browse."""
    if not isinstance(cache, RunExplorerSnapshotCache):
        return None
    if not is_default_recent_browse(
        view=view,
        limit=limit,
        pipeline=pipeline,
        workflow=workflow,
        run_type=run_type,
        run_id=run_id,
        lookup_run_id=lookup_run_id,
    ):
        return None
    return cache.materialize()


async def run_periodic_run_explorer_snapshot(
    cache: RunExplorerSnapshotCache,
    source: _SnapshotSource,
    *,
    interval_seconds: float = RUN_EXPLORER_SNAPSHOT_INTERVAL_SECONDS,
) -> None:
    """Scan once, then sleep only the remainder of the interval."""
    while True:
        started = time.monotonic()
        await cache.refresh_once(source)
        remaining = interval_seconds - (time.monotonic() - started)
        if remaining > 0:
            await asyncio.sleep(remaining)


async def stop_run_explorer_snapshot(task: asyncio.Task[None] | None) -> None:
    """Cancel and join the optional snapshot task."""
    if task is None:
        return
    _ = task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        return


def _without_timing(payload: dict[str, object]) -> dict[str, object]:
    stored = dict(payload)
    items = stored.get("items")
    if not isinstance(items, list):
        return stored
    stripped: list[object] = []
    for item in items:
        if not isinstance(item, dict):
            stripped.append(item)
            continue
        row = dict(item)
        for key in RECENT_TIMING_FIELDS:
            row.pop(key, None)
        stripped.append(row)
    stored["items"] = stripped
    return stored


__all__ = [
    "DEFAULT_RECENT_LIMIT",
    "RUN_EXPLORER_SNAPSHOT_INTERVAL_SECONDS",
    "RunExplorerSnapshotCache",
    "is_default_recent_browse",
    "run_periodic_run_explorer_snapshot",
    "stop_run_explorer_snapshot",
    "take_default_recent_snapshot",
]
