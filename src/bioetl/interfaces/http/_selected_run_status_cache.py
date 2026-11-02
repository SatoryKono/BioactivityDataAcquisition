"""Single-flight TTL cache for selected-run-status payloads (rev7 §3.4).

Owner TTL: 30 seconds fresh. Concurrent callers with the same cache key share
one physical load. Stale entries may be served briefly while a refresh runs.

Bound to a ``HealthServer`` instance (not a process-wide singleton) so distinct
servers with different stores cannot share payloads. Close via ``close()`` on
server stop.
"""

from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from time import monotonic

from bioetl.interfaces.http._forensic_request_budget import ForensicEndpointUnavailable

FRESH_SECONDS = 30.0
MAX_AGE_SECONDS = 90.0
MAX_ENTRIES = 64
_CLOSE_TIMEOUT_SECONDS = 2.0
_LOG = logging.getLogger(__name__)
type StatusKey = tuple[str, str, str, str, str, str]
type StatusLoader = Callable[[], Awaitable[dict[str, object]]]


def selected_run_status_key(query: Mapping[str, str]) -> StatusKey:
    """Normalize the §3.4 key including A2 ``run_status`` filter scope."""

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
        _one("run_status"),
    )


@dataclass
class _Entry:
    payload: dict[str, object] | None = None
    completed_at: float = 0.0
    error: str | None = None


def _is_query_error_payload(payload: Mapping[str, object]) -> bool:
    """True when the loader returned a synthetic QUERY ERROR frame."""
    for key in ("execution_state", "verdict", "status", "overall_verdict"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip().upper() == "QUERY ERROR":
            return True
    reason = payload.get("reason")
    return isinstance(reason, str) and reason in {
        "capacity_exhausted",
        "deadline_exceeded",
        "request_failed",
        "shutting_down",
        "selector_context_mismatch",
    }


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
                if victim is None:
                    raise ForensicEndpointUnavailable(
                        reason="capacity_exhausted", status_code=503
                    )
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
            raise ForensicEndpointUnavailable(reason="shutting_down", status_code=503)
        key = selected_run_status_key(query)
        entry = self._entry(key)
        state = self.status(query)["state"]
        if state == "fresh" and entry.payload is not None:
            return deepcopy(entry.payload)

        task = self._tasks.get(key)
        if task is None:
            task = asyncio.create_task(self._load(key, entry, loader))
            self._tasks[key] = task
            self._observe_background_task(task)

        if state == "stale" and entry.payload is not None:
            # Do not await; refresh continues in background.
            return deepcopy(entry.payload)

        return deepcopy(await asyncio.shield(task))

    @staticmethod
    def _observe_background_task(task: asyncio.Task[dict[str, object]]) -> None:
        """Retrieve background exceptions so the event loop does not warn.

        Cold waiters still observe the same failure when they await ``task``.
        """

        def _done(done: asyncio.Task[dict[str, object]]) -> None:
            if done.cancelled():
                return
            exc = done.exception()
            if exc is not None:
                _LOG.warning(
                    "selected_run_status background refresh failed: %s",
                    type(exc).__name__,
                    exc_info=exc,
                )

        task.add_done_callback(_done)

    async def _load(
        self,
        key: StatusKey,
        entry: _Entry,
        loader: StatusLoader,
    ) -> dict[str, object]:
        try:
            payload = await loader()
            if _is_query_error_payload(payload):
                # Keep last good snapshot; do not promote QUERY ERROR to fresh.
                # Still return the error frame to this caller so Grafana sees it.
                entry.error = "QUERY_ERROR"
                return deepcopy(payload)
            entry.payload = deepcopy(payload)
            entry.completed_at = monotonic()
            entry.error = None
            return deepcopy(payload)
        except (ForensicEndpointUnavailable, ValueError, OSError, RuntimeError) as exc:
            entry.error = (
                exc.reason
                if isinstance(exc, ForensicEndpointUnavailable)
                else type(exc).__name__
            )
            raise
        finally:
            self._tasks.pop(key, None)

    async def close(self) -> None:
        self._closed = True
        if not self._tasks:
            return
        pending = tuple(self._tasks.values())
        _done, still = await asyncio.wait(pending, timeout=_CLOSE_TIMEOUT_SECONDS)
        for task in still:
            task.cancel()
        if still:
            # Drain cancellations inside the same shutdown budget; do not start
            # another full timeout window.
            await asyncio.gather(*still, return_exceptions=True)


__all__ = [
    "FRESH_SECONDS",
    "MAX_AGE_SECONDS",
    "MAX_ENTRIES",
    "SelectedRunStatusCache",
    "selected_run_status_key",
]
