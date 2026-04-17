"""Regression checks for local Codex skills/agents setup scripts."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_setup_agents_dry_run_lists_expected_agent_entries(tmp_path: Path) -> None:
    """setup_agents dry-run should enumerate the agent surface it will sync."""
    root = _project_root()
    env = os.environ | {"CODEX_HOME": str(tmp_path / ".codex-home")}

    result = subprocess.run(
        ["bash", "scripts/ops/launchers/codex/setup_agents.sh", "--dry-run"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Would sync:" in result.stdout
    assert "ORCHESTRATION.md" in result.stdout
    assert "py-test-bot.md" in result.stdout
    assert "subagents" in result.stdout


def test_setup_skills_dry_run_includes_paired_agent_sync_by_default(
    tmp_path: Path,
) -> None:
    """setup_skills should announce paired agent sync unless disabled."""
    root = _project_root()
    env = os.environ | {"CODEX_HOME": str(tmp_path / ".codex-home")}

    result = subprocess.run(
        ["bash", "scripts/ops/launchers/codex/setup_skills.sh", "--dry-run"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Would sync:" in result.stdout
    assert "py-test-bot ->" in result.stdout
    assert "would also sync paired agents" in result.stdout
    assert "py-test-bot.md" in result.stdout


def test_setup_plugins_uses_repo_root_from_ops_directory() -> None:
    """setup_plugins must resolve the repository root, not scripts/."""
    root = _project_root()
    content = (
        root / "scripts/ops/launchers/codex/setup_plugins.sh"
    ).read_text(encoding="utf-8")

    assert 'REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"' in content


def test_setup_plugins_prefers_local_venv_and_windows_git_fallback() -> None:
    """setup_plugins should avoid uv when a working local venv already exists."""
    root = _project_root()
    content = (
        root / "scripts/ops/launchers/codex/setup_plugins.sh"
    ).read_text(encoding="utf-8")

    assert 'if [[ -x ".venv/Scripts/python.exe" ]]; then' in content
    assert "elif command -v uv >/dev/null 2>&1; then" in content
    assert "\\$env:Path='C:\\\\Program Files\\\\Git\\\\cmd;'+\\$env:Path" in content
    assert "\\$env:PRE_COMMIT_HOME=" in content
