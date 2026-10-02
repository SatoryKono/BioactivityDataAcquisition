"""Preserve inventory CLI modes after retiring the subprocess wrapper."""

from __future__ import annotations

import pytest

from scripts.engineering.repo import __main__ as router

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("options", "mode"),
    [([], "--update"), (["--write"], "--update"), (["--check"], "--check")],
)
def test_sync_inventory_preserves_modes_and_manifest(monkeypatch, options, mode):
    calls = []

    def dispatch(args, **kwargs):
        calls.append(args)
        return 17

    monkeypatch.setattr(router, "dispatch_cli", dispatch)
    assert router.main(["sync-inventory", *options, "--manifest", "custom.json"]) == 17
    assert calls == [["sync-inventory", mode, "--manifest", "custom.json"]]
    assert router.COMMANDS["sync-inventory"] == router.COMMANDS["check-inventory"]


def test_sync_inventory_rejects_conflicting_modes():
    with pytest.raises(SystemExit) as raised:
        router.main(["sync-inventory", "--write", "--check"])
    assert raised.value.code == 2
