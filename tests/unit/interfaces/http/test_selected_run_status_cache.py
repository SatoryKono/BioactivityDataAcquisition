"""Single-flight TTL cache for selected-run-status (rev7 §3.4)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from bioetl.interfaces.http import _selected_run_status_cache as module

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

QUERY = {
    "pipeline": "chembl_assay",
    "run_id": "run-1",
    "run_type": "full",
    "workflow": "chembl_assay",
}
PAYLOAD = {"pipeline": "chembl_assay", "run_id": "run-1", "verdict": "OK"}


async def _read(cache: module.SelectedRunStatusCache, loader, query=None):
    return await cache.read(QUERY if query is None else query, loader)


async def test_twenty_cold_clients_share_one_load() -> None:
    cache = module.SelectedRunStatusCache()
    started, release = asyncio.Event(), asyncio.Event()

    async def load() -> dict[str, object]:
        started.set()
        await release.wait()
        return dict(PAYLOAD)

    loader = AsyncMock(side_effect=load)
    tasks = [asyncio.create_task(_read(cache, loader)) for _ in range(20)]
    await started.wait()
    release.set()
    results = await asyncio.gather(*tasks)
    assert loader.await_count == 1
    assert all(row["run_id"] == "run-1" for row in results)
    results[0]["run_id"] = "mutated"
    assert (await _read(cache, loader))["run_id"] == "run-1"


async def test_fresh_hit_skips_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [0.0]
    monkeypatch.setattr(module, "monotonic", lambda: now[0])
    cache = module.SelectedRunStatusCache()
    loader = AsyncMock(return_value=dict(PAYLOAD))
    await _read(cache, loader)
    assert loader.await_count == 1
    now[0] = module.FRESH_SECONDS - 1
    await _read(cache, loader)
    assert loader.await_count == 1


async def test_stale_returns_immediately_and_refreshes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [0.0]
    monkeypatch.setattr(module, "monotonic", lambda: now[0])
    cache = module.SelectedRunStatusCache()
    loader = AsyncMock(return_value=dict(PAYLOAD))
    await _read(cache, loader)
    now[0] = module.FRESH_SECONDS + 1
    started, release = asyncio.Event(), asyncio.Event()

    async def slow() -> dict[str, object]:
        started.set()
        await release.wait()
        return {"pipeline": "chembl_assay", "run_id": "run-1", "verdict": "WARN"}

    slow_loader = AsyncMock(side_effect=slow)
    stale = await _read(cache, slow_loader)
    assert stale["verdict"] == "OK"
    await started.wait()
    release.set()
    await asyncio.gather(*cache._tasks.values())
    assert (await _read(cache, AsyncMock(return_value=dict(PAYLOAD))))["verdict"] == (
        "WARN"
    )


async def test_cache_key_normalizes_blank_run_id() -> None:
    assert module.selected_run_status_key(
        {"pipeline": "p", "run_id": "", "run_type": "t", "workflow": "w"}
    ) == ("selected-run-status", "p", "-", "t", "w")
