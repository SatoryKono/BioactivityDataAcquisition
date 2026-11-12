"""Worktree guard tests: filesystem fixtures and mocked Git, never real worktrees."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.engineering.repo import create_worktree as guard

pytestmark = pytest.mark.unit
SHA = "a" * 40


def test_router_refuses_creation_without_mandatory_helper(monkeypatch):
    from scripts.engineering.repo import __main__ as router

    monkeypatch.setattr(guard, "main", lambda *_: pytest.fail("Must not create"))
    with pytest.raises(SystemExit, match="installed bioetl-create-worktree.py"):
        router.main(["worktree", "safe-task", "--no-checkout"])


@pytest.mark.parametrize(
    "ref", ["--help", "-c", "main\n--force", "HEAD:path", "a;calc"]
)
def test_revision_rejects_options_and_expressions_before_git(ref, monkeypatch):
    monkeypatch.setattr(guard, "_git", lambda *_: pytest.fail("Git must not run"))
    with pytest.raises(ValueError, match="Invalid Git revision"):
        guard._revision(Path("D:/github/repo"), ref)


@pytest.mark.parametrize("argument", ["main\n--force", "$(calc)", "a;calc", "a b"])
def test_git_argument_allowlist_blocks_before_subprocess(argument, monkeypatch):
    monkeypatch.setattr(
        subprocess, "run", lambda *_a, **_k: pytest.fail("Must not run")
    )
    with pytest.raises(ValueError, match="unsupported characters"):
        guard._git(Path("D:/github/repo"), "rev-parse", argument)


def test_branch_option_is_rejected_before_native_branch_check(policy, git_calls):
    with pytest.raises(SystemExit):
        guard.main(["safe-task", "--branch=--help", "--no-checkout"])
    assert not any(args[0] == "check-ref-format" for _, args in git_calls)
    assert not guard.WORKTREE_ROOT.exists()


@pytest.mark.parametrize("status", ["FAIL", "ERROR", "SKIP"])
def test_shared_guard_non_pass_blocks_git_creation(
    policy, git_calls, monkeypatch, status
):
    from types import SimpleNamespace

    original = guard.runpy.run_path

    def refused(path):
        namespace = original(path)
        namespace["revalidate_worktree"] = lambda *_a, **_k: SimpleNamespace(
            status=status, code="worktree.race"
        )
        return namespace

    monkeypatch.setattr(guard.runpy, "run_path", refused)
    with pytest.raises(SystemExit):
        guard.main(["safe-task", "--no-checkout"])
    assert not any(args[:2] == ("worktree", "add") for _, args in git_calls)
    assert not guard.WORKTREE_ROOT.exists()


def test_shared_guard_revalidates_immediately_before_add(
    policy, git_calls, monkeypatch
):
    events = []
    original_load = guard.runpy.run_path
    original_git = guard._git

    def loaded(path):
        namespace = original_load(path)
        original_check = namespace["revalidate_worktree"]

        def checked(*args, **kwargs):
            events.append("revalidate")
            return original_check(*args, **kwargs)

        namespace["revalidate_worktree"] = checked
        return namespace

    def tracked_git(repo, *args):
        events.append(args[:2])
        return original_git(repo, *args)

    monkeypatch.setattr(guard.runpy, "run_path", loaded)
    monkeypatch.setattr(guard, "_git", tracked_git)
    guard.main(["safe-task", "--no-checkout"])
    assert events[-2:] == ["revalidate", ("worktree", "add")]


@pytest.fixture
def policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    approved = (tmp_path / "approved").resolve()
    approved.mkdir()
    repo = approved / "primary"
    (repo / ".git").mkdir(parents=True)
    implementation = repo / "scripts/engineering/repo/create_worktree.py"
    implementation.parent.mkdir(parents=True)
    implementation.write_text(
        "def main():\n    print('tracked implementation')\n    return 0\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(guard, "APPROVED_ROOT", approved)
    monkeypatch.setattr(
        guard, "WORKTREE_ROOT", approved / "BioactivityDataAcquisition-worktrees"
    )
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
def test_native_validate_only_creates_no_tree(tmp_path: Path) -> None:
    task = "guard-preflight-" + tmp_path.name
    target = Path("D:/github/BioactivityDataAcquisition-worktrees") / task
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "scripts.engineering.repo",
            "worktree",
            task,
            "--validate-only",
        ],
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
        [
            sys.executable,
            "-B",
            "-m",
            "scripts.engineering.repo",
            "worktree",
            "safe-task",
            "--validate-only",
        ],
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
    before = template.stat().st_mtime_ns if template.exists() else None
    sha = guard._revision(repo, "HEAD")
    with pytest.raises(ValueError, match="explicit per-task user approval"):
        guard._check_env(repo, sha, False)
    after = template.stat().st_mtime_ns if template.exists() else None
    assert after == before


def test_git_paths_decode_as_utf8_under_legacy_windows_locale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import locale

    monkeypatch.setattr(locale, "getencoding", lambda: "cp1252")
    original = subprocess.run

    def checked_run(*args, **kwargs):
        assert kwargs["encoding"] == "utf-8"
        return original(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", checked_run)
    repo = Path(__file__).resolve().parents[5]
    sha = guard._revision(repo, "HEAD")
    paths = guard._git(repo, "ls-tree", "-rz", "--name-only", sha, "--")
    assert "docs/99-archive/plans/наблюдаемость.md\0" in paths
    guard._check_env(repo, sha, True)


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


@pytest.mark.parametrize(
    "variable",
    [
        "GIT_DIR",
        "GIT_COMMON_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG_SYSTEM",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "git_work_tree",
    ],
)
def test_git_execution_cannot_inherit_repository_or_config_redirects(
    policy: Path,
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
) -> None:
    monkeypatch.setenv(variable, "synthetic-redirect")
    monkeypatch.setenv("GIT_NO_REPLACE_OBJECTS", "0")
    monkeypatch.setenv("BIOETL_FIXTURE_PASSTHROUGH", "preserved")
    environments = []

    def fake_run(command, **kwargs):
        environments.append(kwargs.get("env"))
        return subprocess.CompletedProcess(command, 0, stdout="synthetic output\n")

    monkeypatch.setattr(guard.subprocess, "run", fake_run)
    assert guard._git(policy, "rev-parse", "--show-toplevel") == "synthetic output\n"
    environment = environments[0]
    assert environment is not None
    assert {key.upper() for key in environment if key.upper().startswith("GIT_")} == {
        "GIT_NO_REPLACE_OBJECTS"
    }
    assert environment["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert environment["BIOETL_FIXTURE_PASSTHROUGH"] == "preserved"
    assert os.environ[variable] == "synthetic-redirect"
