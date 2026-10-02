"""Bounded, single-flight snapshots of fully projected selector options."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from time import monotonic

from bioetl.application.runtime_clock import current_utc_time
from bioetl.interfaces.http._forensic_request_budget import (
    ForensicEndpointUnavailable,
    run_bounded_forensic_operation,
)

FRESH_SECONDS = 30.0
MAX_AGE_SECONDS = 120.0
RETRY_SECONDS = 5.0
MAX_ENTRIES = 32
MAX_REFRESHES = 4
_ENDPOINT = "/ops/control-plane/filter-options"
type SelectorKey = tuple[tuple[str, str], ...]
type OptionsLoader = Callable[[], Awaitable[dict[str, object]]]


def selector_options_key(query: Mapping[str, str]) -> SelectorKey:
    """Preserve all response-affecting parameters, excluding transport controls."""
    normalized = {
        key: value
        for key, value in query.items()
        if key not in {"allow_stale", "status_only"}
    }
    normalized.setdefault("dimension", "run_id")
    normalized.setdefault("response_shape", "object")
    normalized.setdefault("timezone", "UTC")
    return tuple(sorted(normalized.items()))


@dataclass
class _Entry:
    payload: dict[str, object] | None = None
    completed_at: float = 0.0
    observed_at: str | None = None
    snapshot_id: str | None = None
    error: str | None = None
    retry_at: float = 0.0


class SelectorOptionsCache:
    """Keep last good options while bounded refreshes update them atomically."""

    def __init__(self) -> None:
        self._entries: OrderedDict[SelectorKey, _Entry] = OrderedDict()
        self._tasks: dict[SelectorKey, asyncio.Task[None]] = {}
        self._closed = False

    def status(self, query: Mapping[str, str]) -> dict[str, object]:
        """Inspect one exact query without admission, refresh, or disk reads."""
        key = selector_options_key(query)
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
            "snapshot_id": entry.snapshot_id,
            "observed_at": entry.observed_at,
            "age_seconds": age,
            "refresh_in_progress": key in self._tasks,
            "last_refresh_error": entry.error,
        }

    def _entry(self, key: SelectorKey) -> _Entry:
        if key not in self._entries:
            if len(self._entries) >= MAX_ENTRIES:
                victim = next(
                    (item for item in self._entries if item not in self._tasks), None
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
        loader: OptionsLoader,
        *,
        limiter: asyncio.Semaphore,
        timeout_seconds: float,
        queue_timeout_seconds: float,
    ) -> dict[str, object]:
        """Serve usable options immediately; cold callers share one bounded wait."""
        if self._closed:
            raise ForensicEndpointUnavailable(reason="shutting_down", status_code=503)
        key = selector_options_key(query)
        entry = self._entry(key)
        state = self.status(query)["state"]
        if state == "fresh":
            return self._response(query, entry)
        if (
            key not in self._tasks
            and monotonic() >= entry.retry_at
            and len(self._tasks) < MAX_REFRESHES
        ):
            self._tasks[key] = asyncio.create_task(
                self._refresh(
                    key,
                    entry,
                    loader,
                    limiter,
                    timeout_seconds,
                    queue_timeout_seconds,
                )
            )
        if state == "stale":
            return self._response(query, entry)
        task = self._tasks.get(key)
        if task is not None:
            try:
                await asyncio.wait_for(
                    asyncio.shield(task), timeout_seconds + queue_timeout_seconds
                )
            except TimeoutError as exc:
                raise ForensicEndpointUnavailable(
                    reason="deadline_exceeded", status_code=504
                ) from exc
        if self.status(query)["state"] == "unavailable":
            raise ForensicEndpointUnavailable(
                reason=entry.error or "capacity_exhausted",
                status_code=504 if entry.error == "deadline_exceeded" else 503,
            )
        return self._response(query, entry)

    def _response(self, query: Mapping[str, str], entry: _Entry) -> dict[str, object]:
        payload = deepcopy(entry.payload or {})
        status = self.status(query)
        payload["catalog"] = status
        items = payload.get("items")
        if status["state"] == "stale" and isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and "text" in item:
                    item["text"] = f"{item['text']} [STALE catalog]"
        return payload

    async def _refresh(
        self,
        key: SelectorKey,
        entry: _Entry,
        loader: OptionsLoader,
        limiter: asyncio.Semaphore,
        timeout: float,
        queue_timeout: float,
    ) -> None:
        work: asyncio.Task[dict[str, object]] | None = None

        async def load() -> dict[str, object]:
            nonlocal work
            work = asyncio.ensure_future(loader())
            return await asyncio.shield(work)

        try:
            payload = await run_bounded_forensic_operation(
                limiter=limiter,
                operation_factory=load,
                timeout_seconds=timeout,
                queue_timeout_seconds=queue_timeout,
                endpoint=_ENDPOINT,
            )
            entry.payload = deepcopy(payload)
            entry.completed_at = monotonic()
            entry.observed_at = current_utc_time().isoformat()
            entry.snapshot_id = hashlib.sha256(
                json.dumps([key, payload], sort_keys=True, ensure_ascii=False).encode(
                    "utf-8"
                )
            ).hexdigest()
            entry.error = None
        except (ForensicEndpointUnavailable, ValueError, OSError, RuntimeError) as exc:
            entry.error = (
                exc.reason
                if isinstance(exc, ForensicEndpointUnavailable)
                else "catalog_refresh_failed"
            )
        finally:
            # A timed-out thread-backed read is still real work. Keep its key
            # occupied until it drains, preventing duplicate refreshes.
            if work is not None and not work.done():
                await asyncio.gather(asyncio.shield(work), return_exceptions=True)
            self._tasks.pop(key, None)
            if entry.error:
                entry.retry_at = monotonic() + RETRY_SECONDS

    async def close(self, timeout_seconds: float = 2.0) -> None:
        """Stop admission and bound shutdown without cancelling live disk reads."""
        self._closed = True
        if self._tasks:
            await asyncio.wait(tuple(self._tasks.values()), timeout=timeout_seconds)
