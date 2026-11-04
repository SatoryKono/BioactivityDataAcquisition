"""Single-flight TTL cache for selected-run-status (rev7 §3.4)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from bioetl.interfaces.http import _selected_run_status_cache as module
from bioetl.interfaces.http._forensic_request_budget import ForensicEndpointUnavailable

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

QUERY = {
    "pipeline": "chembl_assay",
    "run_id": "run-1",
    "run_type": "full",
    "workflow": "chembl_assay",
    "run_status": "success",
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


async def test_cache_key_includes_run_status_and_normalizes_blank_run_id() -> None:
    expected = ("selected-run-status", "p", "-", "t", "w", "failed")
    for run_id in ("", "-", "All", "$__all", "__all", "*"):
        assert (
            module.selected_run_status_key(
                {
                    "pipeline": "p",
                    "run_id": run_id,
                    "run_type": "t",
                    "workflow": "w",
                    "run_status": "failed",
                }
            )
            == expected
        )
    success = module.selected_run_status_key(
        {
            "pipeline": "p",
            "run_id": "-",
            "run_type": "t",
            "workflow": "w",
            "run_status": "success",
        }
    )
    failed = module.selected_run_status_key(
        {
            "pipeline": "p",
            "run_id": "-",
            "run_type": "t",
            "workflow": "w",
            "run_status": "failed",
        }
    )
    assert success != failed
    concrete = module.selected_run_status_key(
        {
            "pipeline": "p",
            "run_id": "run-1",
            "run_type": "t",
            "workflow": "w",
            "run_status": "failed",
        }
    )
    assert concrete == ("selected-run-status", "p", "run-1", "t", "w", "failed")
    assert concrete != expected


async def test_capacity_exhausted_when_all_entries_busy() -> None:
    cache = module.SelectedRunStatusCache()
    started = asyncio.Event()
    release = asyncio.Event()

    async def hang() -> dict[str, object]:
        started.set()
        await release.wait()
        return dict(PAYLOAD)

    hang_loader = AsyncMock(side_effect=hang)
    tasks = []
    for index in range(module.MAX_ENTRIES):
        query = {**QUERY, "run_id": f"run-{index}"}
        tasks.append(asyncio.create_task(_read(cache, hang_loader, query=query)))
    await started.wait()
    # Give the event loop a turn so every task has entered _entry/_load.
    await asyncio.sleep(0)
    with pytest.raises(ForensicEndpointUnavailable) as exc_info:
        await _read(
            cache,
            AsyncMock(return_value=dict(PAYLOAD)),
            query={**QUERY, "run_id": "overflow"},
        )
    assert exc_info.value.reason == "capacity_exhausted"
    release.set()
    await asyncio.gather(*tasks)


async def test_query_error_payload_does_not_poison_fresh_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [0.0]
    monkeypatch.setattr(module, "monotonic", lambda: now[0])
    cache = module.SelectedRunStatusCache()
    await _read(cache, AsyncMock(return_value=dict(PAYLOAD)))
    error_payload = {
        "pipeline": "chembl_assay",
        "run_id": "run-1",
        "execution_state": "QUERY ERROR",
        "reason": "deadline_exceeded",
    }
    # Expire so the caller awaits the QUERY ERROR refresh.
    now[0] = module.MAX_AGE_SECONDS + 1
    errored = await _read(cache, AsyncMock(return_value=error_payload))
    assert errored["execution_state"] == "QUERY ERROR"
    assert cache.status(QUERY)["last_refresh_error"] == "QUERY_ERROR"
    # Last good snapshot was retained (not replaced by QUERY ERROR).
    stored = cache._entries[module.selected_run_status_key(QUERY)].payload
    assert stored is not None and stored["verdict"] == "OK"
    # Successful reload restores a fresh hit.
    assert (await _read(cache, AsyncMock(return_value=dict(PAYLOAD))))["verdict"] == (
        "OK"
    )


@pytest.mark.parametrize(
    "reason", ["evidence_corrupt", "identity_mismatch", "revision_missing"]
)
async def test_forensic_source_error_reason_does_not_poison_cache(
    monkeypatch: pytest.MonkeyPatch, reason: str
) -> None:
    now = [0.0]
    monkeypatch.setattr(module, "monotonic", lambda: now[0])
    cache = module.SelectedRunStatusCache()
    await _read(cache, AsyncMock(return_value=dict(PAYLOAD)))
    now[0] = module.MAX_AGE_SECONDS + 1
    error_payload = {"pipeline": "chembl_assay", "run_id": "run-1", "reason": reason}

    assert await _read(cache, AsyncMock(return_value=error_payload)) == error_payload
    assert cache.status(QUERY)["last_refresh_error"] == "QUERY_ERROR"
    stored = cache._entries[module.selected_run_status_key(QUERY)].payload
    assert stored == PAYLOAD


async def test_loader_exception_keeps_last_good_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [0.0]
    monkeypatch.setattr(module, "monotonic", lambda: now[0])
    cache = module.SelectedRunStatusCache()
    await _read(cache, AsyncMock(return_value=dict(PAYLOAD)))
    # Expire past MAX_AGE so the caller must await the failing refresh.
    now[0] = module.MAX_AGE_SECONDS + 1
    with pytest.raises(ForensicEndpointUnavailable):
        await _read(
            cache,
            AsyncMock(
                side_effect=ForensicEndpointUnavailable(
                    reason="deadline_exceeded", status_code=504
                )
            ),
        )
    assert cache.status(QUERY)["last_refresh_error"] == "deadline_exceeded"
    # Last good payload is retained even though age exceeds MAX_AGE.
    assert cache._entries[module.selected_run_status_key(QUERY)].payload == PAYLOAD
    # A successful reload restores freshness.
    assert (await _read(cache, AsyncMock(return_value=dict(PAYLOAD))))["verdict"] == (
        "OK"
    )


async def test_close_rejects_new_reads() -> None:
    cache = module.SelectedRunStatusCache()
    await cache.close()
    with pytest.raises(ForensicEndpointUnavailable) as exc_info:
        await _read(cache, AsyncMock(return_value=dict(PAYLOAD)))
    assert exc_info.value.reason == "shutting_down"


async def test_stale_refresh_exception_is_observed_without_poisoning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [0.0]
    monkeypatch.setattr(module, "monotonic", lambda: now[0])
    cache = module.SelectedRunStatusCache()
    await _read(cache, AsyncMock(return_value=dict(PAYLOAD)))
    now[0] = module.FRESH_SECONDS + 1
    fail = ForensicEndpointUnavailable(reason="deadline_exceeded", status_code=504)
    stale = await _read(cache, AsyncMock(side_effect=fail))
    assert stale["verdict"] == "OK"
    await asyncio.gather(*tuple(cache._tasks.values()), return_exceptions=True)
    assert cache.status(QUERY)["last_refresh_error"] == "deadline_exceeded"
    # Last good snapshot remains; cold waiters can still observe a raised error
    # on a fully expired key in a separate scenario.
    assert cache._entries[module.selected_run_status_key(QUERY)].payload == PAYLOAD


async def test_close_cancels_pending_tasks_after_wait_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = module.SelectedRunStatusCache()
    release = asyncio.Event()

    async def hang() -> dict[str, object]:
        await release.wait()
        return dict(PAYLOAD)

    task = asyncio.create_task(_read(cache, AsyncMock(side_effect=hang)))
    await asyncio.sleep(0)
    assert cache._tasks
    monkeypatch.setattr(module, "_CLOSE_TIMEOUT_SECONDS", 0.01)
    await cache.close()
    assert all(item.cancelled() or item.done() for item in cache._tasks.values()) or (
        not cache._tasks
    )
    release.set()
    await asyncio.gather(task, return_exceptions=True)
