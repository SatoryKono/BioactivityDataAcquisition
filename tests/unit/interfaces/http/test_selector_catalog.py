"""Selector availability, scan sharing, and freshness regressions."""

from __future__ import annotations

import asyncio
from threading import Event
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.interfaces.http import _health_server_routing_support as routing
from bioetl.interfaces.http import _selector_catalog as catalog_module
from bioetl.interfaces.http._selector_catalog import SelectorCatalog
from bioetl.interfaces.http.health_server import HealthServer

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_report_index_scan_is_shared_scoped_and_expires_without_caching_errors(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(catalog_module, "monotonic", lambda: clock[0])
    catalog = SelectorCatalog()
    loader = MagicMock(return_value=[])
    scopes = {"pipeline": ("chembl_activity",), "workflow": ("workflow_a",)}
    await asyncio.gather(*(catalog.read_reports(scopes, loader) for _ in range(8)))
    loader.assert_called_once_with({"pipeline": ("chembl_activity",)})
    await catalog.read_reports({**scopes, "workflow": ("workflow_b",)}, loader)
    assert loader.call_count == 1
    await catalog.read_reports({"pipeline": ("chembl_assay",)}, loader)
    assert loader.call_count == 2
    clock[0] = 5.0
    loader.side_effect = OSError("unreadable report index")
    with pytest.raises(OSError, match="unreadable report index"):
        await catalog.read_reports({"pipeline": ("chembl_assay",)}, loader)
    loader.side_effect = None
    assert await catalog.read_reports({"pipeline": ("chembl_assay",)}, loader) == []
    assert loader.call_count == 4


@pytest.mark.asyncio
async def test_report_index_scan_survives_cancelled_waiter():
    catalog = SelectorCatalog()
    started, release = Event(), Event()

    def load(scopes):
        started.set()
        assert release.wait(5)
        return []

    loader = MagicMock(side_effect=load)
    first = asyncio.create_task(catalog.read_reports({}, loader))
    try:
        assert await asyncio.to_thread(started.wait, 5)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        second = asyncio.create_task(catalog.read_reports({}, loader))
        await asyncio.sleep(0)
        release.set()
        assert await second == []
        loader.assert_called_once()
    finally:
        release.set()


@pytest.mark.asyncio
async def test_concurrent_readers_share_scan_and_cancelled_waiter_does_not_cancel_it():
    catalog = SelectorCatalog()
    started, release = Event(), Event()
    manifests = MagicMock()

    def read():
        started.set()
        assert release.wait(5)
        return ()

    manifests.list_all.side_effect = read
    first = asyncio.create_task(catalog.read(manifests, None))
    try:
        assert await asyncio.to_thread(started.wait, 5)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        others = [asyncio.create_task(catalog.read(manifests, None)) for _ in range(8)]
        await asyncio.sleep(0)
        release.set()
        assert await asyncio.gather(*others) == [((), ())] * 8
        manifests.list_all.assert_called_once()
    finally:
        release.set()


@pytest.mark.asyncio
async def test_snapshot_expires_and_refresh_errors_do_not_serve_stale_catalog(
    monkeypatch,
):
    clock = [0.0]
    monkeypatch.setattr(catalog_module, "monotonic", lambda: clock[0])
    manifests = MagicMock()
    manifests.list_all.side_effect = [(), OSError("unreadable catalog"), ()]
    catalog = SelectorCatalog()
    assert await catalog.read(manifests, None) == ((), ())
    clock[0] = 4.0
    assert await catalog.read(manifests, None) == ((), ())
    manifests.list_all.assert_called_once()
    clock[0] = 5.0
    with pytest.raises(OSError, match="unreadable catalog"):
        await catalog.read(manifests, None)
    assert await catalog.read(manifests, None) == ((), ())
    assert manifests.list_all.call_count == 3


@pytest.mark.asyncio
async def test_failed_scan_drains_sibling_before_retry():
    catalog = SelectorCatalog()
    started, release = Event(), Event()
    manifests, workflows = MagicMock(), MagicMock()
    manifests.list_all.side_effect = ValueError("corrupt manifest")

    def read_workflows():
        started.set()
        assert release.wait(5)
        return ()

    workflows.list_all.side_effect = read_workflows
    first = asyncio.create_task(catalog.read(manifests, workflows))
    try:
        assert await asyncio.to_thread(started.wait, 5)
        second = asyncio.create_task(catalog.read(manifests, workflows))
        await asyncio.sleep(0)
        assert not first.done()
        release.set()
        results = await asyncio.gather(first, second, return_exceptions=True)
        assert all(isinstance(result, ValueError) for result in results)
        manifests.list_all.assert_called_once()
        workflows.list_all.assert_called_once()
    finally:
        release.set()


@pytest.mark.asyncio
async def test_filter_options_remain_available_with_all_forensic_slots_occupied(
    monkeypatch,
):
    host = HealthServer()
    host._send_payload_response = AsyncMock()
    monkeypatch.setattr(
        routing, "_filter_options_payload", AsyncMock(return_value={"items": []})
    )
    for _ in range(4):
        await host._forensic_endpoint_limiter.acquire()
    await asyncio.wait_for(
        routing.handle_control_plane_filter_options(host, None, {}), 1
    )
    host._send_payload_response.assert_awaited_once_with(None, 200, {"items": []})
    assert host._forensic_endpoint_limiter.locked()
    assert not host._selector_endpoint_limiter.locked()


@pytest.mark.asyncio
async def test_selector_timeout_retains_slot_until_operation_finishes(monkeypatch):
    host = HealthServer()
    host._selector_endpoint_limiter = asyncio.Semaphore(1)
    host._send_payload_response = AsyncMock()
    release = asyncio.Event()

    async def blocked(*args):
        await release.wait()
        return {"items": []}

    monkeypatch.setattr(routing, "_filter_options_payload", blocked)
    monkeypatch.setattr(routing, "_FILTER_OPTIONS_TIMEOUT_SECONDS", 0.01)
    try:
        await routing.handle_control_plane_filter_options(host, None, {})
        assert host._send_payload_response.call_args.args[1] == 504
        assert host._selector_endpoint_limiter.locked()
    finally:
        release.set()
    await asyncio.wait_for(host._selector_endpoint_limiter.acquire(), 1)
    host._selector_endpoint_limiter.release()
