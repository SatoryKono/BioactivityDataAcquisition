"""Contracts for lock-backed local tooling without installing dependencies."""

from __future__ import annotations

import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]
ROOT = Path(__file__).resolve().parents[6]


def test_ruff_hook_matches_locked_version() -> None:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    versions = {
        entry["version"] for entry in lock["package"] if entry["name"] == "ruff"
    }
    assert len(versions) == 1
    config = yaml.safe_load(
        (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    )
    hook = next(
        repo
        for repo in config["repos"]
        if repo["repo"] == "https://github.com/astral-sh/ruff-pre-commit"
    )
    assert hook["rev"] == f"v{versions.pop()}"


def _run_windows_installer(
    tmp_path: Path, *, fail_command: str = "", agent_tools: str = "none"
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    if os.name != "nt":
        pytest.skip("Native Windows bootstrap uses PowerShell and Windows paths")
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        pytest.skip("PowerShell is unavailable")
    capture = tmp_path / "commands.log"
    launcher = tmp_path / "bootstrap_probe.ps1"
    launcher.write_text(
        """param([string]$Installer, [string]$Capture, [string]$FailCommand, [string]$AgentTools)
$ErrorActionPreference = "Stop"
# Keep captured errors independent of terminal width and ConciseView wrapping.
$ErrorView = "NormalView"
function global:uv {
    $command = $args -join " "
    Add-Content -LiteralPath $Capture -Value $command
    if ($command -eq $FailCommand) {
        $global:LASTEXITCODE = 1
    } else {
        $global:LASTEXITCODE = 0
    }
}
& $Installer -AgentTools $AgentTools
exit $LASTEXITCODE
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(launcher),
            "-Installer",
            str(ROOT / "scripts/engineering/dev/setup_env_windows.ps1"),
            "-Capture",
            str(capture),
            "-FailCommand",
            fail_command,
            "-AgentTools",
            agent_tools,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    commands = (
        capture.read_text(encoding="utf-8-sig").splitlines() if capture.exists() else []
    )
    return result, commands


@pytest.mark.parametrize("agent_tools, sync_count", [("none", 1), ("all", 3)])
def test_windows_checks_lock_before_venv_and_frozen_sync(
    tmp_path: Path, agent_tools: str, sync_count: int
) -> None:
    result, commands = _run_windows_installer(tmp_path, agent_tools=agent_tools)
    assert result.returncode == 0, result.stdout + result.stderr
    assert commands[0] == "lock --check"
    assert commands[1].startswith("venv ")
    syncs = [command for command in commands if command.startswith("sync ")]
    assert len(syncs) == sync_count
    assert all("--active --frozen" in command for command in syncs)
    assert all(
        "--extra dev --extra tests --extra tracing" in command for command in syncs
    )


def test_windows_stale_lock_stops_before_environment_changes(tmp_path: Path) -> None:
    result, commands = _run_windows_installer(tmp_path, fail_command="lock --check")
    assert result.returncode != 0
    assert commands == ["lock --check"]
    assert "uv.lock is stale or unavailable" in result.stderr
    assert "Environment ready" not in result.stdout
