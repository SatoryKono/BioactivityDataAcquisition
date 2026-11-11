"""Hook discovery must not execute repository-controlled code."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts.ai.codex import hook_inventory as inventory

pytestmark = pytest.mark.unit


def test_launcher_and_stale_metadata_do_not_establish_version(tmp_path: Path) -> None:
    launcher = tmp_path / "codex.cmd"
    launcher.write_text("exit /b 99", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"version":"999.0"}', encoding="utf-8")
    result = inventory.runtime_inventory(tmp_path, "codex", str(launcher))
    assert result["version"] is None
    assert result["capability_status"] == "NOT_PROVEN"
    assert not result["enabled_by_diagnostic"]


def test_configured_hook_is_not_execution_proof(tmp_path: Path) -> None:
    path = tmp_path / ".devin/hooks.v1.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"PreToolUse": [{"hooks": [{"command": "never-run"}]}]}))
    result = inventory.runtime_inventory(tmp_path, "devin", None)
    assert result["configured_events"] == ["PreToolUse"]
    assert result["version_status"] == "MISSING"
    assert result["execution"] == "NOT_PROVEN"


def test_invalid_config_is_error_without_contents(tmp_path: Path) -> None:
    config = tmp_path / ".junie/config.json"
    config.parent.mkdir()
    config.write_text("secret-invalid-content")
    result = inventory.runtime_inventory(tmp_path, "junie", None)
    assert result["config_status"] == "ERROR"
    assert "secret-invalid-content" not in json.dumps(result)


def test_git_query_failure_is_not_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: object, **kwargs: object) -> str:
        raise subprocess.TimeoutExpired("git", 3)

    monkeypatch.setattr(inventory, "_git", fail)
    assert inventory.git_inventory(tmp_path)["status"] == "ERROR"


def test_collect_never_executes_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(inventory.shutil, "which", lambda name: "/untrusted/" + name)
    monkeypatch.setattr(inventory, "git_inventory", lambda root: {"status": "OBSERVED"})

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("runtime or hook execution attempted")

    monkeypatch.setattr(inventory.subprocess, "run", forbidden)
    result = inventory.collect(tmp_path)
    assert result["status"] == "NOT_PROVEN"
    assert len(result["runtimes"]) == 4


def test_effective_git_directory_is_used(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hooks = tmp_path / "shared-hooks"
    hooks.mkdir()
    (hooks / "pre-commit.sample").write_text("sample")
    monkeypatch.setattr(inventory, "_git", lambda *args: str(hooks))
    result = inventory.git_inventory(tmp_path)
    assert result["directory"] == str(hooks.resolve())
    assert not any(hook["discoverable"] for hook in result["hooks"])
