"""Preserve inventory CLI modes after retiring the subprocess wrapper."""

from __future__ import annotations

import importlib
import sys

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


@pytest.mark.parametrize(
    ("command", "module_name"),
    [
        ("checks", "scoped_checks"),
        ("closeout", "closeout_runtime"),
        ("hooks", "hook_installation"),
    ],
)
@pytest.mark.parametrize("exit_code", [0, 2, 3, 130])
def test_direct_facades_preserve_arguments_and_exit_status(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    module_name: str,
    exit_code: int,
) -> None:
    module = importlib.import_module(f"scripts.engineering.repo.{module_name}")
    calls = []

    def invoke(args: list[str]) -> int:
        calls.append(args)
        return exit_code

    monkeypatch.setattr(sys, "path", sys.path.copy())
    monkeypatch.setattr(module, "main", invoke)
    monkeypatch.setattr(
        router, "dispatch_cli", lambda *args, **kwargs: pytest.fail("wrong dispatch")
    )
    assert router.main([command, "--fixture-argument"]) == exit_code
    assert calls == [["--fixture-argument"]]
