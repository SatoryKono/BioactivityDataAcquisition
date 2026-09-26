"""Default Run Explorer browse is served from memory with a request-time age."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from urllib.parse import parse_qs, urlsplit

import pytest

from bioetl.interfaces.http import _health_server_observability_routing as routing
from bioetl.interfaces.http import _run_explorer_snapshot as snapshot_module
from bioetl.interfaces.http._run_explorer_snapshot import (
    RunExplorerSnapshotCache,
    is_default_recent_browse,
    run_periodic_run_explorer_snapshot,
    stop_run_explorer_snapshot,
)
from bioetl.interfaces.http.health_server import HealthServer
from bioetl.interfaces.http.health_server_routing_mixin import HealthServerRoutingMixin

pytestmark = pytest.mark.unit

_COMPLETED = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
_DEFAULT_URL = (
    "/ops/observability/pipeline-run-reports"
    "?pipeline=.*&limit=10&run_id=-&view=recent"
    "&workflow=.*&run_type=.*&lookup_run_id="
)


def _row(*, age_label: str = "STALE") -> dict[str, object]:
    return {
        "run_id": "kept",
        "status": "success",
        "started_at": (_COMPLETED - timedelta(seconds=10)).isoformat(),
        "completed_at": _COMPLETED.isoformat(),
        "last_event_at": _COMPLETED.isoformat(),
        "event_age_display": age_label,
        "last_event_age_seconds": 1,
    }


def _page() -> dict[str, object]:
    return {
        "order_by": "started_at_desc",
        "index_state": "ok",
        "items": [_row()],
        "count": 1,
    }


def _parsed_default_query() -> dict[str, str]:
    parsed = parse_qs(urlsplit(_DEFAULT_URL).query, keep_blank_values=False)
    return {key: values[-1] for key, values in parsed.items() if values}


def _browse_kwargs(query: dict[str, str], *, limit: int) -> dict[str, object]:
    read = HealthServerRoutingMixin._read_optional_param
    return {
        "view": query.get("view"),
        "limit": limit,
        "pipeline": read(query, "pipeline"),
        "workflow": read(query, "workflow"),
        "run_type": read(query, "run_type"),
        "run_id": read(query, "run_id"),
        "lookup_run_id": read(query, "lookup_run_id"),
    }


def test_parsed_default_url_is_the_hot_key() -> None:
    query = _parsed_default_query()
    assert "lookup_run_id" not in query
    assert is_default_recent_browse(**_browse_kwargs(query, limit=10))
    scoped = dict(query)
    scoped["workflow"] = "daily"
    assert not is_default_recent_browse(**_browse_kwargs(scoped, limit=10))


@pytest.mark.asyncio
async def test_refresh_strips_cached_age_and_materialize_uses_request_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[dict[str, object]] = []

    def _scan(**kwargs: object) -> dict[str, object]:
        seen.append(kwargs)
        return _page()

    monkeypatch.setattr(snapshot_module, "list_recent_pipeline_runs", _scan)
    cache = RunExplorerSnapshotCache()
    source = SimpleNamespace(_run_manifest_port=object(), _run_ledger_port=object())
    await cache.refresh_once(source)
    assert seen[0]["limit"] == 10
    assert seen[0]["pipeline"] == ".*"
    assert seen[0]["selected_run_id"] == "-"
    stored = cache._stored
    assert stored is not None
    stored_items = stored["items"]
    assert isinstance(stored_items, list)
    stored_row = stored_items[0]
    assert isinstance(stored_row, dict)
    assert "event_age_display" not in stored_row

    body = cache.materialize(now=_COMPLETED + timedelta(seconds=90))
    assert body is not None
    items = body["items"]
    assert isinstance(items, list)
    first = items[0]
    assert isinstance(first, dict)
    assert first["event_age_display"] == "1 m 30 s"
    assert first["last_event_age_seconds"] == 90
    later = cache.materialize(now=_COMPLETED + timedelta(seconds=120))
    assert later is not None
    later_items = later["items"]
    assert isinstance(later_items, list)
    later_row = later_items[0]
    assert isinstance(later_row, dict)
    assert later_row["event_age_display"] == "2 m"
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_failed_refresh_keeps_the_last_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    def _scan(**_kwargs: object) -> dict[str, object]:
        calls["count"] += 1
        if calls["count"] > 1:
            raise RuntimeError("scan failed")
        return _page()

    monkeypatch.setattr(snapshot_module, "list_recent_pipeline_runs", _scan)
    cache = RunExplorerSnapshotCache()
    source = SimpleNamespace(_run_manifest_port=object(), _run_ledger_port=object())
    await cache.refresh_once(source)
    await cache.refresh_once(source)
    body = cache.materialize(now=_COMPLETED + timedelta(seconds=90))
    assert body is not None
    items = body["items"]
    assert isinstance(items, list)
    row = items[0]
    assert isinstance(row, dict)
    assert row["run_id"] == "kept"
    assert row["event_age_display"] == "1 m 30 s"


@pytest.mark.asyncio
async def test_periodic_scan_waits_out_the_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered = 0

    def _scan(**_kwargs: object) -> dict[str, object]:
        nonlocal entered
        entered += 1
        return _page()

    monkeypatch.setattr(snapshot_module, "list_recent_pipeline_runs", _scan)
    cache = RunExplorerSnapshotCache()
    source = SimpleNamespace(_run_manifest_port=object(), _run_ledger_port=object())
    task = asyncio.create_task(
        run_periodic_run_explorer_snapshot(cache, source, interval_seconds=30)
    )
    for _ in range(50):
        if cache.materialize(now=_COMPLETED) is not None:
            break
        await asyncio.sleep(0.01)
    await asyncio.sleep(0.05)
    assert entered == 1
    await stop_run_explorer_snapshot(task)
    assert task.done()


@pytest.mark.asyncio
async def test_default_request_uses_snapshot_without_another_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = Mock(side_effect=AssertionError("live catalog scan"))
    monkeypatch.setattr(routing, "list_recent_pipeline_runs", catalog)
    monkeypatch.setattr(
        snapshot_module,
        "current_utc_time",
        lambda: _COMPLETED + timedelta(seconds=90),
    )
    cache = RunExplorerSnapshotCache()
    cache._stored = snapshot_module._without_timing(_page())
    host = SimpleNamespace(
        _read_optional_param=HealthServerRoutingMixin._read_optional_param,
        _run_manifest_port=Mock(),
        _run_ledger_port=Mock(),
        _run_explorer_snapshot=cache,
        _send_payload_response=AsyncMock(),
    )
    await routing.handle_pipeline_run_reports_list(host, None, _parsed_default_query())
    catalog.assert_not_called()
    payload = host._send_payload_response.await_args.args[2]
    assert payload["items"][0]["event_age_display"] == "1 m 30 s"


@pytest.mark.asyncio
async def test_scoped_request_still_scans_when_snapshot_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = Mock(return_value={"items": [], "order_by": "started_at_desc"})
    monkeypatch.setattr(routing, "list_recent_pipeline_runs", catalog)
    cache = RunExplorerSnapshotCache()
    cache._stored = _page()
    host = SimpleNamespace(
        _read_optional_param=HealthServerRoutingMixin._read_optional_param,
        _run_manifest_port=Mock(),
        _run_ledger_port=Mock(),
        _run_explorer_snapshot=cache,
        _send_payload_response=AsyncMock(),
    )
    query = _parsed_default_query()
    query["workflow"] = "daily"
    await routing.handle_pipeline_run_reports_list(host, None, query)
    catalog.assert_called_once()
    assert catalog.call_args.kwargs["workflow"] == "daily"


@pytest.mark.asyncio
async def test_server_start_publishes_snapshot_until_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = asyncio.Event()

    async def _hold(
        _cache: RunExplorerSnapshotCache,
        _source: object,
        *,
        interval_seconds: float = 1.0,
    ) -> None:
        del interval_seconds
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(
        "bioetl.interfaces.http.health_server.run_periodic_run_explorer_snapshot",
        _hold,
    )
    server = HealthServer(
        host="127.0.0.1",
        port=0,
        run_manifest_port=Mock(),
    )
    task: asyncio.Task[None] | None = None
    await server.start()
    try:
        await asyncio.wait_for(started.wait(), timeout=2)
        task = server._run_explorer_refresh_task
        assert task is not None
    finally:
        await server.stop()
    assert server._run_explorer_refresh_task is None
    assert task is not None
    assert task.done()
