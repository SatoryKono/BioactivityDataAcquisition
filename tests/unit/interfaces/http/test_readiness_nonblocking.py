"""A slow durable-history check must leave the HTTP event loop responsive."""

import asyncio
from threading import Event
from unittest.mock import Mock

import pytest

from bioetl.interfaces.http import _health_server_readiness as readiness


@pytest.mark.asyncio
async def test_slow_reconciliation_allows_other_requests_to_progress(monkeypatch):
    if asyncio.to_thread.__module__ != "asyncio.threads":
        pytest.skip(
            reason="requires real asyncio.to_thread worker offload; "
            "the WSL safeguard in tests/conftest.py runs it inline"
        )
    entered, release = Event(), Event()
    host = Mock(_health_monitor=None)
    host._response_timestamp.return_value = "2026-09-15T00:00:00+00:00"
    monkeypatch.setattr(
        readiness, "report_root_readiness_check", lambda: {"status": "healthy"}
    )
    monkeypatch.setattr(readiness, "enforce_report_root_marker", lambda: True)
    monkeypatch.setattr(readiness, "create_run_report_store", Mock())

    def slow_check(**_kwargs):
        entered.set()
        assert release.wait(timeout=2), "HTTP event loop blocked by reconciliation"
        return {"status": "healthy"}

    monkeypatch.setattr(readiness, "current_metrics_reconciliation_check", slow_check)
    task = asyncio.create_task(readiness.build_readiness_response(host))
    try:
        assert await asyncio.to_thread(entered.wait, 2)
        # This coroutine represents another HTTP request on the same event loop.
        await asyncio.sleep(0)
        release.set()
        response = await task
        assert response.status == "healthy"
        assert response.checks["current_metrics"] == {"status": "healthy"}
    finally:
        release.set()
        if not task.done():
            await task
