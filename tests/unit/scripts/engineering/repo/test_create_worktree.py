"""Worktree guard tests: filesystem fixtures and mocked Git, never real worktrees."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from scripts.engineering.repo import create_worktree as guard

pytestmark = pytest.mark.unit
SHA = "a" * 40


@pytest.fixture
def policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    approved = (tmp_path / "approved").resolve()
    approved.mkdir()
    repo = approved / "primary"
    (repo / ".git").mkdir(parents=True)
    implementation = repo / "scripts/engineering/repo/create_worktree.py"
    implementation.parent.mkdir(parents=True)
    implementation.write_text("print('tracked implementation')\n", encoding="utf-8")
    monkeypatch.setattr(guard, "APPROVED_ROOT", approved)
    monkeypatch.setattr(guard, "WORKTREE_ROOT", approved / "worktrees")
    monkeypatch.setattr(guard, "_require_windows", lambda: None)
    monkeypatch.setattr(guard, "_source_repo", lambda: repo)
    return repo


@pytest.fixture
def git_calls(
    policy: Path, monkeypatch: pytest.MonkeyPatch
) -> list[tuple[Path, tuple[str, ...]]]:
    calls: list[tuple[Path, tuple[str, ...]]] = []

    def fake_git(repo: Path, *args: str) -> str:
        calls.append((repo, args))
        if "--git-common-dir" in args:
            return str(policy / ".git") + "\n"
        if args[0] == "rev-parse":
            return SHA + "\n"
        if args[0] == "ls-tree":
            return "README.md\0.env.example\0"
        if args[:2] == ("worktree", "add"):
            # Plain fixture directory only: no Git metadata or .env file is made.
            Path(args[-2]).mkdir(parents=True)
        return ""

    monkeypatch.setattr(guard, "_git", fake_git)
    return calls


@pytest.mark.parametrize(
    "value",
    ["../escape", "bad/child", "NUL", "aux.txt", "COM9", "trailing.", "a\\..\\escape"],
)
def test_unsafe_destination_is_rejected_before_git(
    policy: Path, git_calls: list, value: str
) -> None:
    with pytest.raises(SystemExit) as error:
        guard.main([value])
    assert error.value.code == 2
    assert git_calls == []


def test_absolute_outside_and_existing_targets_are_rejected(
    policy: Path, git_calls: list
) -> None:
    with pytest.raises(ValueError):
        guard.validate_destination(str(policy.parent.parent / "outside"))
    existing = guard.WORKTREE_ROOT / "existing"
    existing.mkdir(parents=True)
    with pytest.raises(ValueError, match="already exists"):
        guard.validate_destination(str(existing))
    assert git_calls == []


def test_validate_only_is_side_effect_free(policy: Path, git_calls: list) -> None:
    before = sorted(policy.parent.rglob("*"))
    assert guard.main(["safe-task", "--validate-only"]) == 0
    assert (
        guard.validate_destination(str(guard.WORKTREE_ROOT / "safe-task"))
        == guard.WORKTREE_ROOT / "safe-task"
    )
    assert sorted(policy.parent.rglob("*")) == before
    assert git_calls == []


def _directory_link(link: Path, target: Path) -> None:
    if os.name == "nt":
        link_literal = str(link).replace("'", "''")
        target_literal = str(target).replace("'", "''")
        script = f"New-Item -ItemType Junction -Path '{link_literal}' -Target '{target_literal}' -ErrorAction Stop | Out-Null\n"
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", "-"],
            input=script,
            check=True,
            capture_output=True,
            text=True,
        )
    else:
        link.symlink_to(target, target_is_directory=True)


@pytest.mark.parametrize(
    "surface", ["parent", "destination", "approved-root", "hooks", "metadata"]
)
def test_existing_junction_or_symlink_escape_is_rejected(
    policy: Path,
    git_calls: list,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    if surface == "approved-root":
        link = tmp_path / "redirected-root"
        _directory_link(link, outside)
        monkeypatch.setattr(guard, "APPROVED_ROOT", link)
    elif surface == "parent":
        _directory_link(guard.WORKTREE_ROOT, outside)
    elif surface == "destination":
        guard.WORKTREE_ROOT.mkdir()
        _directory_link(guard.WORKTREE_ROOT / "safe-task", outside)
    elif surface == "metadata":
        (policy / ".git").rmdir()  # Empty, test-owned fixture only.
        _directory_link(policy / ".git", outside)
    else:
        _directory_link(policy / ".git/hooks", outside)
    with pytest.raises(ValueError):
        guard.install_helper() if surface in (
            "hooks",
            "metadata",
        ) else guard.validate_destination("safe-task")
    assert git_calls == []


def test_checkout_requires_actual_template_approval(
    policy: Path, git_calls: list
) -> None:
    with pytest.raises(SystemExit) as error:
        guard.main(["safe-task"])
    assert error.value.code == 2
    assert not any(args[:2] == ("worktree", "add") for _, args in git_calls)
    assert not guard.WORKTREE_ROOT.exists()


@pytest.mark.parametrize(
    "env_path", [".env", ".env.production", "config/.env.example", ".ENV.local"]
)
def test_template_flag_cannot_approve_other_env_files(
    policy: Path, monkeypatch: pytest.MonkeyPatch, env_path: str
) -> None:
    monkeypatch.setattr(guard, "_git", lambda *_: env_path + "\0")
    with pytest.raises(ValueError, match="only the tracked root"):
        guard._check_env(policy, SHA, True)


@pytest.mark.parametrize(
    "options", [[], ["--detach"], ["--existing-branch", "codex/existing"]]
)
def test_checkout_is_pinned_and_never_moves_an_existing_ref(
    policy: Path, git_calls: list, options: list[str]
) -> None:
    assert guard.main(["safe-task", "--env-example-approved", *options]) == 0
    add = next(args for _, args in git_calls if args[:2] == ("worktree", "add"))
    if options and options[0] == "--existing-branch":
        assert "--no-checkout" in add and "-b" not in add
        assert any(args == ("read-tree", "--reset", "-u", SHA) for _, args in git_calls)
    else:
        assert add[-1] == SHA
    assert not list(guard.WORKTREE_ROOT.rglob(".env*"))


def test_no_checkout_does_not_need_env_approval(policy: Path, git_calls: list) -> None:
    assert guard.main(["safe-task", "--no-checkout"]) == 0
    assert not any(args[0] in ("ls-tree", "read-tree") for _, args in git_calls)
    assert "--no-checkout" in next(
        args for _, args in git_calls if args[:2] == ("worktree", "add")
    )


def test_existing_branch_drift_is_reported_without_reset(
    policy: Path, git_calls: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = guard._git

    def moved(repo: Path, *args: str) -> str:
        result = original(repo, *args)
        return "b" * 40 if args and args[-1] == "HEAD^{commit}" else result

    monkeypatch.setattr(guard, "_git", moved)
    with pytest.raises(SystemExit) as error:
        guard.main(
            [
                "safe-task",
                "--existing-branch",
                "codex/existing",
                "--env-example-approved",
            ]
        )
    assert error.value.code == 2
    assert (guard.WORKTREE_ROOT / "safe-task").is_dir()
    assert not any(
        args[0] in ("reset", "update-ref", "branch") for _, args in git_calls
    )


def test_installer_is_idempotent_and_delegates_to_tracked_source(policy: Path) -> None:
    target = guard.install_helper()
    before = target.stat().st_mtime_ns
    assert guard.install_helper() == target
    assert target.stat().st_mtime_ns == before
    result = subprocess.run(
        [sys.executable, "-B", str(target)], check=True, capture_output=True, text=True
    )
    assert result.stdout.strip() == "tracked implementation"


def test_installer_preserves_unmanaged_helper(policy: Path) -> None:
    target = policy / ".git/hooks" / guard.HELPER_NAME
    target.parent.mkdir()
    target.write_text("local customization\n", encoding="utf-8")
    with pytest.raises(ValueError, match="preserve"):
        guard.install_helper()
    assert target.read_text(encoding="utf-8") == "local customization\n"


@pytest.mark.skipif(
    os.name != "nt" or not Path("D:/github").is_dir(),
    reason="Requires approved native Windows workspace",
)
def test_native_validate_only_creates_no_tree() -> None:
    task = "guard-preflight-" + uuid.uuid4().hex
    target = Path("D:/github/BioactivityDataAcquisition-worktrees") / task
    result = subprocess.run(
        [sys.executable, "-B", guard.__file__, task, "--validate-only"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert Path(result.stdout.strip()) == target
    assert not target.exists()


@pytest.mark.skipif(
    os.name == "nt", reason="POSIX unavailable-platform negative control"
)
def test_non_windows_cli_fails_closed() -> None:
    result = subprocess.run(
        [sys.executable, "-B", guard.__file__, "safe-task", "--validate-only"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "Use Windows Python" in result.stderr


def test_git_common_metadata_escape_blocks_creation(
    policy: Path, git_calls: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(guard, "_git", lambda *_: str(policy.parent.parent / "outside"))
    with pytest.raises(SystemExit) as error:
        guard.main(["safe-task", "--env-example-approved"])
    assert error.value.code == 2
    assert not guard.WORKTREE_ROOT.exists()


def test_real_read_only_git_preflight_requires_template_consent() -> None:
    repo = Path(__file__).resolve().parents[5]
    template = repo / ".env.example"
    before = template.stat().st_mtime_ns
    sha = guard._revision(repo, "HEAD")
    with pytest.raises(ValueError, match="explicit per-task user approval"):
        guard._check_env(repo, sha, False)
    assert template.stat().st_mtime_ns == before


def test_new_foreign_files_are_preserved_before_existing_branch_population(
    policy: Path, git_calls: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = guard._git
    foreign = guard.WORKTREE_ROOT / "safe-task" / "foreign.txt"

    def changed(repo: Path, *args: str) -> str:
        result = original(repo, *args)
        if args[:2] == ("worktree", "add"):
            foreign.write_text("preserve me", encoding="utf-8")
        return result

    monkeypatch.setattr(guard, "_git", changed)
    with pytest.raises(SystemExit) as error:
        guard.main(
            [
                "safe-task",
                "--existing-branch",
                "codex/existing",
                "--env-example-approved",
            ]
        )
    assert error.value.code == 2
    assert foreign.read_text(encoding="utf-8") == "preserve me"
    assert not any(args[0] == "read-tree" for _, args in git_calls)
