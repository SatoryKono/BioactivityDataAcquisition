"""Single-flight TTL cache for selected-run-status payloads (rev7 §3.4).

Owner TTL: 30 seconds fresh. Concurrent callers with the same cache key share
one physical load. Stale entries may be served briefly while a refresh runs.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from time import monotonic
from typing import Any

FRESH_SECONDS = 30.0
MAX_AGE_SECONDS = 90.0
MAX_ENTRIES = 64
type StatusKey = tuple[str, str, str, str, str]
type StatusLoader = Callable[[], Awaitable[dict[str, object]]]


def selected_run_status_key(query: Mapping[str, str]) -> StatusKey:
    """Normalize the §3.4 key: endpoint + pipeline + run_id + run_type + workflow."""

    def _one(name: str) -> str:
        raw = query.get(name)
        if raw is None:
            return ""
        return str(raw).strip()

    return (
        "selected-run-status",
        _one("pipeline"),
        _one("run_id") or "-",
        _one("run_type"),
        _one("workflow"),
    )


@dataclass
class _Entry:
    payload: dict[str, object] | None = None
    completed_at: float = 0.0
    error: str | None = None


class SelectedRunStatusCache:
    """Deduplicate concurrent selected-run-status loads per scope key."""

    def __init__(self) -> None:
        self._entries: OrderedDict[StatusKey, _Entry] = OrderedDict()
        self._tasks: dict[StatusKey, asyncio.Task[dict[str, object]]] = {}
        self._closed = False

    def status(self, query: Mapping[str, str]) -> dict[str, object]:
        key = selected_run_status_key(query)
        entry = self._entries.get(key, _Entry())
        age = (
            max(0.0, monotonic() - entry.completed_at)
            if entry.payload is not None
            else None
        )
        state = "unavailable"
        if age is not None and age < MAX_AGE_SECONDS:
            state = "fresh" if age < FRESH_SECONDS else "stale"
        return {
            "state": state,
            "age_seconds": age,
            "refresh_in_progress": key in self._tasks,
            "last_refresh_error": entry.error,
        }

    def _entry(self, key: StatusKey) -> _Entry:
        if key not in self._entries:
            if len(self._entries) >= MAX_ENTRIES:
                victim = next(
                    (item for item in self._entries if item not in self._tasks),
                    None,
                )
                if victim is not None:
                    del self._entries[victim]
            self._entries[key] = _Entry()
        self._entries.move_to_end(key)
        return self._entries[key]

    async def read(
        self,
        query: Mapping[str, str],
        loader: StatusLoader,
    ) -> dict[str, object]:
        if self._closed:
            raise RuntimeError("selected-run-status cache is closed")
        key = selected_run_status_key(query)
        entry = self._entry(key)
        state = self.status(query)["state"]
        if state == "fresh" and entry.payload is not None:
            return deepcopy(entry.payload)

        task = self._tasks.get(key)
        if task is None:
            task = asyncio.create_task(self._load(key, entry, loader))
            self._tasks[key] = task

        if state == "stale" and entry.payload is not None:
            # Do not await; refresh continues in background.
            return deepcopy(entry.payload)

        try:
            return deepcopy(await asyncio.shield(task))
        finally:
            # Task removal happens in _load; no-op if already cleaned.
            pass

    async def _load(
        self,
        key: StatusKey,
        entry: _Entry,
        loader: StatusLoader,
    ) -> dict[str, object]:
        try:
            payload = await loader()
            entry.payload = deepcopy(payload)
            entry.completed_at = monotonic()
            entry.error = None
            return deepcopy(payload)
        except Exception as exc:  # noqa: BLE001 — surface to callers as-is
            entry.error = type(exc).__name__
            raise
        finally:
            self._tasks.pop(key, None)

    async def close(self) -> None:
        self._closed = True
        if self._tasks:
            await asyncio.wait(tuple(self._tasks.values()), timeout=2.0)


# Process-local shared cache for the health server.
_SHARED: SelectedRunStatusCache | None = None


def shared_selected_run_status_cache() -> SelectedRunStatusCache:
    global _SHARED
    if _SHARED is None:
        _SHARED = SelectedRunStatusCache()
    return _SHARED


def reset_shared_selected_run_status_cache_for_tests() -> None:
    """Test helper: drop the process-local singleton."""
    global _SHARED
    _SHARED = None


__all__ = [
    "FRESH_SECONDS",
    "MAX_AGE_SECONDS",
    "MAX_ENTRIES",
    "SelectedRunStatusCache",
    "reset_shared_selected_run_status_cache_for_tests",
    "selected_run_status_key",
    "shared_selected_run_status_cache",
]
