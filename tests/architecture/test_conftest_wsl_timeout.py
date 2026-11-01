"""Regression tests for pytest configuration on WSL."""

from __future__ import annotations

import asyncio
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
