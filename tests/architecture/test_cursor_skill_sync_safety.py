"""Safety contracts for Cursor skill synchronization."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = [
    pytest.mark.architecture,
    pytest.mark.skipif(
        sys.platform.startswith("win"),
        reason="symlink safety contract is exercised through the Bash entrypoint",
    ),
]

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/ai/cursor/setup_skills.sh"


def _sandbox(tmp_path: Path, *skill_names: str) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    script = repo / "scripts/ai/cursor/setup_skills.sh"
    script.parent.mkdir(parents=True)
    shutil.copy2(SCRIPT, script)
    for name in skill_names:
        (repo / ".codex/skills" / name).mkdir(parents=True)
    return repo, script, tmp_path / "cursor-home"


def _run_sync(
    repo: Path,
    script: Path,
    cursor_home: Path,
    *args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script), *args],
        cwd=repo,
        env={**os.environ, "CURSOR_HOME": str(cursor_home)},
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("args", [(), ("--dry-run",)])
def test_existing_project_and_user_skill_directories_fail_closed(
    tmp_path: Path,
    args: tuple[str, ...],
) -> None:
    repo, script, cursor_home = _sandbox(tmp_path, "owned-name")
    project_target = repo / ".cursor/skills/owned-name"
    user_target = cursor_home / "skills/owned-name"
    project_target.mkdir(parents=True)
    user_target.mkdir(parents=True)
    project_marker = project_target / "project-owned.txt"
    user_marker = user_target / "user-owned.txt"
    project_marker.touch()
    user_marker.touch()

    result = _run_sync(repo, script, cursor_home, *args)

    assert result.returncode != 0
    assert "Collision:" in result.stderr
    assert "Skill sync aborted" in result.stderr
    assert project_marker.is_file()
    assert user_marker.is_file()


def test_only_managed_project_symlinks_are_pruned(tmp_path: Path) -> None:
    repo, script, cursor_home = _sandbox(tmp_path, "active")
    project_skills = repo / ".cursor/skills"
    project_skills.mkdir(parents=True)
    active_link = project_skills / "active"
    stale_link = project_skills / "stale"
    active_link.symlink_to("../../.codex/skills/active")
    stale_link.symlink_to("../../.codex/skills/stale")
    custom_user_skill = cursor_home / "skills/custom"
    custom_user_skill.mkdir(parents=True)
    marker = custom_user_skill / "keep.txt"
    marker.touch()

    result = _run_sync(repo, script, cursor_home)

    assert result.returncode == 0, result.stderr
    assert active_link.is_symlink()
    assert os.readlink(active_link) == "../../.codex/skills/active"
    assert not stale_link.exists() and not stale_link.is_symlink()
    user_link = cursor_home / "skills/active"
    assert user_link.is_symlink()
    assert os.readlink(user_link) == str(repo / ".codex/skills/active")
    assert marker.is_file()


def test_unmanaged_stale_symlink_is_preserved_and_blocks_sync(
    tmp_path: Path,
) -> None:
    repo, script, cursor_home = _sandbox(tmp_path, "active")
    project_skills = repo / ".cursor/skills"
    project_skills.mkdir(parents=True)
    external_target = tmp_path / "external-skill"
    external_target.mkdir()
    stale_link = project_skills / "custom"
    stale_link.symlink_to(external_target)

    result = _run_sync(repo, script, cursor_home, "--project-only")

    assert result.returncode != 0
    assert "stale entry is not a managed skill symlink" in result.stderr
    assert stale_link.is_symlink()
    assert stale_link.resolve() == external_target


def test_dry_run_reports_actions_without_creating_skill_roots(
    tmp_path: Path,
) -> None:
    repo, script, cursor_home = _sandbox(tmp_path, "active")

    result = _run_sync(repo, script, cursor_home, "--dry-run")

    assert result.returncode == 0, result.stderr
    assert "create directory:" in result.stdout
    assert "create:" in result.stdout
    assert not (repo / ".cursor/skills").exists()
    assert not (cursor_home / "skills").exists()
