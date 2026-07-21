"""Regression tests for the Codex MCP persistence helper."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "ai" / "codex" / "helper" / "ensure-mcp.sh"


def _prepare_workspace(root: Path) -> None:
    payload = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    for relative_path in (
        ".mcp.json",
        "scripts/ai/.mcp.json",
        ".vscode/mcp.json",
        ".qodo/mcp.json",
        ".zed/mcp.json",
        ".devin/config.json",
    ):
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_codex_config(home: Path, workspace: Path, *, valid: bool) -> Path:
    config_path = home / ".codex" / "config.toml"
    config_path.parent.mkdir(parents=True)
    filesystem_section = ""
    if valid:
        filesystem_section = f"""
[mcp_servers.filesystem]
command = "npx"
args = ["{workspace}"]
"""
    config_path.write_text(
        (
            f"""[mcp_servers.memory]
command = "npx"
args = ["{workspace}"]
"""
            + filesystem_section
        ),
        encoding="utf-8",
    )
    return config_path


def _run_helper(
    workspace: Path, home: Path, mode: str
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "REPO_ROOT": str(workspace),
            "CODEX_VALIDATE_MCP_LIST": "0",
        }
    )
    return subprocess.run(
        ["bash", str(SCRIPT), mode],
        cwd=workspace,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


@pytest.mark.skipif(
    sys.platform == "win32", reason="bash helper is exercised in the WSL runtime"
)
def test_ensure_keeps_valid_persisted_config_unchanged(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    home = tmp_path / "home"
    workspace.mkdir()
    home.mkdir()
    _prepare_workspace(workspace)
    config_path = _write_codex_config(home, workspace, valid=True)
    original = config_path.read_text(encoding="utf-8")

    result = _run_helper(workspace, home, "--ensure")

    assert result.returncode == 0, result.stderr
    assert "ready (unchanged)" in result.stdout
    assert config_path.read_text(encoding="utf-8") == original
    assert "BEGIN MANAGED MCP SERVERS" not in original


@pytest.mark.skipif(
    sys.platform == "win32", reason="bash helper is exercised in the WSL runtime"
)
def test_ensure_repairs_stale_persisted_config(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    home = tmp_path / "home"
    workspace.mkdir()
    home.mkdir()
    _prepare_workspace(workspace)
    config_path = _write_codex_config(home, workspace, valid=False)

    result = _run_helper(workspace, home, "--ensure")

    assert result.returncode == 0, result.stderr
    assert "ready (refreshed)" in result.stdout
    rendered = config_path.read_text(encoding="utf-8")
    assert "# === BEGIN MANAGED MCP SERVERS ===" in rendered
    assert "[mcp_servers.filesystem]" in rendered
    assert str(workspace) in rendered
