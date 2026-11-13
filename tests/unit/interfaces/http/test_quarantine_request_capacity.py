"""Every quarantine HTTP reader shares the forensic request budget."""

from __future__ import annotations

import asyncio
from functools import partial
from unittest.mock import AsyncMock, MagicMock
import pytest
from bioetl.interfaces.http.health_server import HealthServer
from bioetl.interfaces.http._health_server_quarantine_routing import (
    dispatch_quarantine_request,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "suffix",
    [
        "filtered-records",
        "filtered-stats",
        "filter-options",
        "filtered-timeseries",
        "filtered-record/hash",
    ],
)
async def test_saturated_capacity_rejects_without_backend_read(suffix):
    service = MagicMock()
    service.list_filtered_records = AsyncMock()
    service.get_filtered_record = AsyncMock()
    service.get_filtered_stats = AsyncMock()
    service.get_filtered_timeseries = AsyncMock()
    service.get_filtered_filter_options = AsyncMock()
    server = HealthServer(quarantine_service=service)
    server._forensic_endpoint_limiter = asyncio.Semaphore(0)
    server._send_payload_response = AsyncMock()
    await dispatch_quarantine_request(
        server,
        writer=MagicMock(),
        path="/ops/quarantine/" + suffix,
        query={"pipeline": "audit"},
    )
    assert server._send_payload_response.await_args.args[1] == 503
    assert all(
        getattr(service, name).await_count == 0
        for name in [
            "list_filtered_records",
            "get_filtered_record",
            "get_filtered_stats",
            "get_filtered_timeseries",
            "get_filtered_filter_options",
        ]
    )


_ROUTES = [
    ("filtered-records", "list_filtered_records"),
    ("filtered-stats", "get_filtered_stats"),
    ("filter-options", "get_filtered_filter_options"),
    ("filtered-timeseries", "get_filtered_timeseries"),
    ("filtered-record/hash", "get_filtered_record"),
]


def _short_budget(monkeypatch):
    from bioetl.interfaces.http import _forensic_request_budget as budget
    from bioetl.interfaces.http import _health_server_quarantine_routing as routing

    monkeypatch.setattr(
        routing,
        "run_bounded_forensic_operation",
        partial(budget.run_bounded_forensic_operation, timeout_seconds=0.01),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("suffix,method", _ROUTES)
async def test_late_backend_never_writes_second_response(monkeypatch, suffix, method):
    _short_budget(monkeypatch)
    released, completed = asyncio.Event(), asyncio.Event()

    async def backend(**kwargs):
        await released.wait()
        completed.set()
        return {"records": []}

    service = MagicMock()
    setattr(service, method, AsyncMock(side_effect=backend))
    server = HealthServer(quarantine_service=service)
    server._send_payload_response = AsyncMock()
    try:
        await dispatch_quarantine_request(
            server,
            writer=MagicMock(),
            path="/ops/quarantine/" + suffix,
            query={"pipeline": "audit"},
        )
        assert [
            call.args[1] for call in server._send_payload_response.await_args_list
        ] == [504]
        assert server._forensic_endpoint_limiter._value == 3
    finally:
        released.set()
        await asyncio.wait_for(completed.wait(), 1)
        await asyncio.sleep(0)
    assert [call.args[1] for call in server._send_payload_response.await_args_list] == [
        504
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("suffix,method", _ROUTES)
async def test_slow_writer_does_not_become_backend_timeout(monkeypatch, suffix, method):
    _short_budget(monkeypatch)
    entered, released = asyncio.Event(), asyncio.Event()
    service = MagicMock()
    setattr(service, method, AsyncMock(return_value={"records": []}))
    server = HealthServer(quarantine_service=service)
    statuses = []

    async def send(writer, status, payload):
        statuses.append(status)
        if status == 200:
            entered.set()
            await released.wait()

    server._send_payload_response = send
    task = asyncio.create_task(
        dispatch_quarantine_request(
            server,
            writer=MagicMock(),
            path="/ops/quarantine/" + suffix,
            query={"pipeline": "audit"},
        )
    )
    try:
        await asyncio.wait_for(entered.wait(), 1)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(asyncio.shield(task), 0.05)
        assert statuses == [200]
    finally:
        released.set()
        await task
