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
"""Regression checks for local Codex skills/agents setup scripts."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from tests.helpers import repo_root, run_repo_command


pytestmark = pytest.mark.architecture

_BASH_DRY_RUN_UNSUPPORTED_ON_WINDOWS = pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="bash-based dry-run scripts are not reliable on native Windows shells",
)


@_BASH_DRY_RUN_UNSUPPORTED_ON_WINDOWS
def test_setup_agents_dry_run_lists_expected_agent_entries(tmp_path: Path) -> None:
    """Canonical setup_agents dry-run should enumerate the agent surface."""
    root = repo_root()
    result = run_repo_command(
        "bash",
        "scripts/ai/codex/setup_agents.sh",
        "--dry-run",
        cwd=root,
        env={"CODEX_HOME": str(tmp_path / ".codex-home")},
    )

    assert result.returncode == 0, result.stderr
    assert "Would sync:" in result.stdout
    assert "ORCHESTRATION.md" in result.stdout
    assert "py-test-bot.md" in result.stdout
    assert "subagents" in result.stdout


@_BASH_DRY_RUN_UNSUPPORTED_ON_WINDOWS
def test_setup_skills_dry_run_includes_paired_agent_sync_by_default(
    tmp_path: Path,
) -> None:
    """Canonical setup_skills should announce paired agent sync unless disabled."""
    root = repo_root()
    result = run_repo_command(
        "bash",
        "scripts/ai/codex/setup_skills.sh",
        "--dry-run",
        cwd=root,
        env={"CODEX_HOME": str(tmp_path / ".codex-home")},
    )

    assert result.returncode == 0, result.stderr
    assert "Would sync:" in result.stdout
    assert "py-test-bot ->" in result.stdout
    assert "would also sync paired agents" in result.stdout
    assert "py-test-bot.md" in result.stdout


def test_ops_router_dispatches_setup_commands_to_canonical_codex_scripts() -> None:
    """scripts.ops should expose setup commands through canonical Codex targets."""
    root = repo_root()
    ops_router = (root / "scripts" / "ops" / "__main__.py").read_text(encoding="utf-8")

    assert "../ai/codex/setup_agents.sh" in ops_router
    assert "../ai/codex/setup_skills.sh" in ops_router
    assert not (
        root / "scripts" / "ops" / "launchers" / "codex" / "setup_agents.sh"
    ).exists()
    assert not (
        root / "scripts" / "ops" / "launchers" / "codex" / "setup_skills.sh"
    ).exists()


def test_setup_plugins_uses_repo_root_from_ops_directory() -> None:
    """setup_plugins must resolve the repository root, not scripts/."""
    root = repo_root()
    content = (root / "scripts/ops/launchers/codex/setup_plugins.sh").read_text(
        encoding="utf-8"
    )

    assert 'REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"' in content


def test_setup_plugins_prefers_local_venv_and_windows_git_fallback() -> None:
    """setup_plugins should avoid uv when a working local venv already exists."""
    root = repo_root()
    content = (root / "scripts/ops/launchers/codex/setup_plugins.sh").read_text(
        encoding="utf-8"
    )

    assert 'WINDOWS_LOCAL_VENV_PYTHON=".venv/Scripts/python.exe"' in content
    assert 'WINDOWS_REPO_VENV_PYTHON=".venv-win/Scripts/python.exe"' in content
    assert '[[ -x "$WINDOWS_LOCAL_VENV_PYTHON" ]]' in content
    assert '[[ -x "$WINDOWS_REPO_VENV_PYTHON" ]]' in content
    assert "elif command -v uv >/dev/null 2>&1; then" in content
    assert "\\$env:Path='C:\\\\Program Files\\\\Git\\\\cmd;'+\\$env:Path" in content
    assert "\\$env:PRE_COMMIT_HOME=" in content


def test_setup_plugins_supports_hook_only_install_and_commit_msg_hook() -> None:
    """setup_plugins should expose a hook-only path and install commit-msg."""
    root = repo_root()
    content = (root / "scripts/ops/launchers/codex/setup_plugins.sh").read_text(
        encoding="utf-8"
    )

    assert "--hooks-only" in content
    assert "--hook-type commit-msg" in content


def test_make_precommit_install_reuses_setup_plugins_helper() -> None:
    """Makefile precommit-install should reuse the canonical setup helper."""
    root = repo_root()
    makefile = (root / "Makefile").read_text(encoding="utf-8")

    assert "bash scripts/ops/launchers/codex/setup_plugins.sh --hooks-only" in makefile
