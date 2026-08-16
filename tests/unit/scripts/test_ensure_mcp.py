# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Regression tests for the Codex MCP persistence helper."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.ai.codex import setup_mcp


pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]


def _to_bash_path(path: Path) -> str:
    value = path.as_posix()
    if len(value) >= 3 and value[1] == ":" and value[2] == "/":
        return f"/mnt/{value[0].lower()}{value[2:]}"
    return value


SCRIPT = _to_bash_path(ROOT / "scripts" / "ai" / "codex" / "helper" / "ensure-mcp.sh")


def _prepare_workspace(root: Path, home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_mcp.Path, "home", lambda: home)
    assert (
        setup_mcp.main(
            [
                "--root",
                str(root),
                "--workspace-root",
                str(root),
                "--profile",
                "stable",
                "--transport-mode",
                "shared",
                "--persist-local-profile",
                "--skip-codex-validation",
            ]
        )
        == 0
    )


def _write_codex_config(home: Path, workspace: Path, *, valid: bool) -> Path:
    config_path = home / ".codex" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if valid:
        # Must match ensure-mcp.sh / DEFAULT_LOCAL_* (stable + shared transport).
        rendered = setup_mcp._render_codex_mcp_toml(
            setup_mcp._codex_runtime_servers(
                workspace,
                profile=setup_mcp.DEFAULT_LOCAL_PROFILE,
                transport_mode=setup_mcp.DEFAULT_LOCAL_TRANSPORT_MODE,
            )
        )
    else:
        rendered = f"""[mcp_servers.memory]
command = "npx"
args = ["{workspace}"]
"""
    config_path.write_text(rendered, encoding="utf-8")
    return config_path


def _run_helper(
    workspace: Path,
    home: Path,
    mode: str,
    *,
    env_updates: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "HOME": _to_bash_path(home),
            "REPO_ROOT": _to_bash_path(workspace),
            "CODEX_VALIDATE_MCP_LIST": "0",
        }
    )
    if env_updates:
        env.update(env_updates)
    return subprocess.run(
        ["bash", SCRIPT, mode],
        cwd=workspace,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        # Structural ensure can still pay Python cold-start on slow mounts;
        # keep above nested generate timeout without racing pytest.
        timeout=60,
    )


@pytest.mark.skipif(
    sys.platform == "win32", reason="bash helper is exercised in the WSL runtime"
)
def test_ensure_keeps_valid_persisted_config_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    home = tmp_path / "home"
    workspace.mkdir()
    home.mkdir()
    _prepare_workspace(workspace, home, monkeypatch)
    config_path = _write_codex_config(home, workspace, valid=True)
    fixed_mtime_ns = 946_684_800_000_000_000
    os.utime(config_path, ns=(fixed_mtime_ns, fixed_mtime_ns))
    original = config_path.read_text(encoding="utf-8")

    result = _run_helper(workspace, home, "--ensure")

    assert result.returncode == 0, result.stderr
    assert "ready" in result.stdout
    assert "ready (unchanged)" in result.stdout or "ready (refreshed)" in result.stdout
    assert config_path.read_text(encoding="utf-8") == original
    if "ready (unchanged)" in result.stdout:
        assert config_path.stat().st_mtime_ns == fixed_mtime_ns
    assert "BEGIN MANAGED MCP SERVERS" in original


@pytest.mark.skipif(
    sys.platform == "win32", reason="bash helper is exercised in the WSL runtime"
)
def test_ensure_repairs_stale_persisted_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    home = tmp_path / "home"
    workspace.mkdir()
    home.mkdir()
    _prepare_workspace(workspace, home, monkeypatch)
    config_path = _write_codex_config(home, workspace, valid=False)

    result = _run_helper(workspace, home, "--ensure")

    assert result.returncode == 0, result.stderr
    assert "ready (refreshed)" in result.stdout
    rendered = config_path.read_text(encoding="utf-8")
    assert "# === BEGIN MANAGED MCP SERVERS ===" in rendered
    assert "[mcp_servers.filesystem]" in rendered
    assert setup_mcp.MCP_SHARED_SERVER_ENDPOINTS["filesystem"] in rendered


@pytest.mark.skipif(
    sys.platform == "win32", reason="bash helper is exercised in the WSL runtime"
)
def test_check_rejects_stale_full_local_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    home = tmp_path / "home"
    workspace.mkdir()
    home.mkdir()
    _prepare_workspace(workspace, home, monkeypatch)

    vscode_path = workspace / ".vscode" / "mcp.json"
    vscode = json.loads(vscode_path.read_text(encoding="utf-8"))
    vscode["servers"]["docker"] = setup_mcp._local_http_server(
        setup_mcp.MCP_SHARED_SERVER_ENDPOINTS["docker"]
    )
    vscode_path.write_text(json.dumps(vscode, indent=2) + "\n", encoding="utf-8")

    result = _run_helper(workspace, home, "--check")

    assert result.returncode != 0
    assert "local MCP projections do not match stable/shared" in result.stdout
    assert ".vscode/mcp.json" in result.stdout
    assert "extra=['docker']" in result.stdout


@pytest.mark.skipif(
    sys.platform == "win32", reason="bash helper is exercised in the WSL runtime"
)
def test_ensure_propagates_governed_timeout_and_reuses_healthy_plane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "workspace"
    home = tmp_path / "home"
    workspace.mkdir()
    home.mkdir()
    _prepare_workspace(workspace, home, monkeypatch)

    runtime_dir = workspace / "scripts" / "ops" / "runtime" / "mcp"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    health = runtime_dir / "health-shared.sh"
    health.write_text(
        """#!/usr/bin/env bash
set -eu
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
[[ -f "${root}/.fake-shared-ready" ]]
""",
        encoding="utf-8",
    )
    launcher = runtime_dir / "start-shared.sh"
    launcher.write_text(
        """#!/usr/bin/env bash
set -eu
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
printf 'start\n' >>"${root}/.fake-shared-starts"
: >"${root}/.fake-shared-ready"
""",
        encoding="utf-8",
    )
    for script in (health, launcher):
        script.chmod(0o755)
    matrix = workspace / "scripts" / "ai" / "codex" / "mcp_profile_contract.py"
    matrix.parent.mkdir(parents=True, exist_ok=True)
    matrix.write_text("print('memory')\n", encoding="utf-8")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    timeout_capture = tmp_path / "timeout.txt"
    fake_timeout = fake_bin / "timeout"
    fake_timeout.write_text(
        """#!/usr/bin/env bash
set -eu
printf '%s\n' "$1" >>"${BIOETL_TEST_CAPTURE:?}"
shift
exec "$@"
""",
        encoding="utf-8",
    )
    fake_timeout.chmod(0o755)
    updates = {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "BIOETL_TEST_CAPTURE": str(timeout_capture),
        "CODEX_MCP_SHARED_START_TIMEOUT": "47",
    }

    first = _run_helper(workspace, home, "--ensure", env_updates=updates)
    second = _run_helper(workspace, home, "--ensure", env_updates=updates)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert timeout_capture.read_text(encoding="utf-8").splitlines() == ["47"]
    assert (workspace / ".fake-shared-starts").read_text(encoding="utf-8") == "start\n"
