"""Availability guarantees for explicitly opted-in selector clients."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from bioetl.interfaces.http import _selector_options_cache as module
from bioetl.interfaces.http._forensic_request_budget import ForensicEndpointUnavailable

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]
QUERY = {"dimension": "workflow", "response_shape": "options"}
PAYLOAD = {"items": [{"text": "assay", "value": "chembl_assay"}]}


async def test_snapshot_identity_tracks_scope_and_content():
    first, second = module.SelectorOptionsCache(), module.SelectorOptionsCache()
    loader = AsyncMock(return_value=PAYLOAD)
    original = (await read(first, loader))["catalog"]["snapshot_id"]
    assert (await read(second, loader))["catalog"]["snapshot_id"] == original
    scoped = await read(second, loader, {**QUERY, "pipeline": "chembl_assay"})
    assert scoped["catalog"]["snapshot_id"] != original
    changed = module.SelectorOptionsCache()
    result = await read(changed, AsyncMock(return_value={"items": []}))
    assert result["catalog"]["snapshot_id"] != original


async def read(cache, loader, query=None, limiter=None, timeout=1):
    return await cache.read(
        QUERY if query is None else query,
        loader,
        limiter=limiter if limiter is not None else asyncio.Semaphore(4),
        timeout_seconds=timeout,
        queue_timeout_seconds=0.02,
    )


async def test_twenty_cold_clients_share_one_refresh_and_cancellation():
    cache = module.SelectorOptionsCache()
    started, release = asyncio.Event(), asyncio.Event()

    async def load():
        started.set()
        await release.wait()
        return PAYLOAD

    loader = AsyncMock(side_effect=load)
    tasks = [asyncio.create_task(read(cache, loader)) for _ in range(20)]
    await started.wait()
    tasks[0].cancel()
    with pytest.raises(asyncio.CancelledError):
        await tasks[0]
    release.set()
    results = await asyncio.gather(*tasks[1:])
    assert loader.await_count == 1
    assert all(row["items"] == PAYLOAD["items"] for row in results)
    assert len({row["catalog"]["snapshot_id"] for row in results}) == 1
    results[0]["items"].clear()
    assert (await read(cache, loader))["items"] == PAYLOAD["items"]


async def test_stale_is_immediate_under_saturation_and_expires(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(module, "monotonic", lambda: now[0])
    cache = module.SelectorOptionsCache()
    loader = AsyncMock(return_value=PAYLOAD)
    await read(cache, loader)
    now[0] = 31
    result = await read(cache, loader, limiter=asyncio.Semaphore(0))
    assert result["catalog"]["state"] == "stale"
    assert result["catalog"]["refresh_in_progress"]
    assert result["items"][0] == {
        "text": "assay [STALE catalog]",
        "value": "chembl_assay",
    }
    await asyncio.gather(*cache._tasks.values())
    assert cache.status(QUERY)["last_refresh_error"] == "capacity_exhausted"
    now[0] = 121
    with pytest.raises(ForensicEndpointUnavailable):
        await read(cache, loader, limiter=asyncio.Semaphore(0))
    assert cache.status(QUERY)["state"] == "unavailable"
    assert loader.await_count == 1


async def test_scope_timezone_policy_isolation_and_no_io_for_ready_options():
    cache = module.SelectorOptionsCache()
    loader = AsyncMock(return_value=PAYLOAD)
    queries = [
        {**QUERY, "pipeline": "A"},
        {**QUERY, "pipeline": "B"},
        {**QUERY, "pipeline": "A", "timezone": "Europe/Kiev"},
        {**QUERY, "pipeline": "A", "exact_run_only": "1"},
    ]
    for query in queries:
        await read(cache, loader, query)
    result = await read(
        cache, loader, {**queries[0], "allow_stale": "1"}, asyncio.Semaphore(0)
    )
    assert result["catalog"]["state"] == "fresh"
    assert loader.await_count == 4
    assert cache.status({**queries[0], "status_only": "1"})["state"] == "fresh"


async def test_timeout_holds_slot_and_single_flight_until_work_drains():
    cache = module.SelectorOptionsCache()
    release = asyncio.Event()
    limiter = asyncio.Semaphore(1)

    async def load():
        await release.wait()
        return PAYLOAD

    loader = AsyncMock(side_effect=load)
    try:
        with pytest.raises(ForensicEndpointUnavailable) as error:
            await read(cache, loader, limiter=limiter, timeout=0.01)
        assert error.value.status_code == 504
        assert limiter.locked()
        assert cache.status(QUERY)["refresh_in_progress"]
        with pytest.raises(ForensicEndpointUnavailable):
            await read(cache, loader, limiter=limiter, timeout=0.01)
        assert loader.await_count == 1
    finally:
        release.set()
        await asyncio.gather(*cache._tasks.values())
        await asyncio.sleep(0)
    assert not limiter.locked()
    assert cache.status(QUERY)["state"] == "unavailable"


async def test_failed_refresh_preserves_good_snapshot_and_throttles_retry(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(module, "monotonic", lambda: now[0])
    cache = module.SelectorOptionsCache()
    loader = AsyncMock(return_value=PAYLOAD)
    initial = await read(cache, loader)
    now[0] = 31
    loader.side_effect = OSError("unreadable source")
    await read(cache, loader)
    await asyncio.gather(*cache._tasks.values())
    for _ in range(20):
        result = await read(cache, loader)
        assert result["catalog"]["snapshot_id"] == initial["catalog"]["snapshot_id"]
        assert result["catalog"]["last_refresh_error"] == "catalog_refresh_failed"
    assert loader.await_count == 2
    await cache.close()
    with pytest.raises(ForensicEndpointUnavailable, match="shutting_down"):
        await read(cache, loader)


async def test_lru_cache_size_is_bounded(monkeypatch):
    monkeypatch.setattr(module, "MAX_ENTRIES", 2)
    cache = module.SelectorOptionsCache()
    loader = AsyncMock(return_value=PAYLOAD)
    for scope in ("A", "B", "A", "C"):
        await read(cache, loader, {**QUERY, "pipeline": scope})
    assert len(cache._entries) == 2
    assert loader.await_count == 3
    assert cache.status({**QUERY, "pipeline": "A"})["state"] == "fresh"
    assert cache.status({**QUERY, "pipeline": "B"})["state"] == "unavailable"


async def test_different_scopes_cannot_exceed_refresh_cap(monkeypatch):
    monkeypatch.setattr(module, "MAX_REFRESHES", 2)
    cache = module.SelectorOptionsCache()
    release = asyncio.Event()

    async def load():
        await release.wait()
        return PAYLOAD

    loader = AsyncMock(side_effect=load)
    tasks = [
        asyncio.create_task(read(cache, loader, {**QUERY, "pipeline": str(i)}))
        for i in range(20)
    ]
    try:
        await asyncio.sleep(0)
        assert len(cache._tasks) == 2
    finally:
        release.set()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    assert loader.await_count == 2
    failures = [
        item for item in results if isinstance(item, ForensicEndpointUnavailable)
    ]
    assert len(failures) == 18
    assert all(item.reason == "capacity_exhausted" for item in failures)
