"""Regression tests for pytest configuration on WSL."""

from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

import pytest

from tests import conftest


@pytest.mark.parametrize("timeout", ["60", "invalid"])
def test_wsl_timeout_updates_parsed_ini_cache_without_inicfg(
    timeout: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(conftest, "_is_wsl", lambda: True)
    monkeypatch.setattr(asyncio, "to_thread", asyncio.to_thread)
    config = SimpleNamespace(
        _inicache={},
        getini=lambda key: timeout if key == "timeout" else None,
    )

    conftest._configure_wsl_timeout(config)

    assert config._inicache["timeout"] == "180"


@pytest.mark.asyncio
async def test_wsl_keeps_synchronization_off_the_event_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    async def threaded(func, /, *_args, **_kwargs):
        calls.append(func)
        return "offloaded"

    monkeypatch.setattr(conftest, "_is_wsl", lambda: True)
    monkeypatch.setattr(asyncio, "to_thread", threaded)
    config = SimpleNamespace(_inicache={}, getini=lambda key: "180")
    conftest._configure_wsl_timeout(config)
    worker = threading.Thread()

    assert await asyncio.to_thread(worker.join) == "offloaded"
    assert calls == [worker.join]
    event = threading.Event()
    assert await asyncio.to_thread(event.wait, 2) == "offloaded"
    assert calls == [worker.join, event.wait]
    assert await asyncio.to_thread(lambda: "inline") == "inline"
    assert calls == [worker.join, event.wait]
