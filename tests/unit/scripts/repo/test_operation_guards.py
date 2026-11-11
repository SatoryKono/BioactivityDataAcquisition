"""Operation guards must deny before execution without writing environment files."""

from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.engineering.repo import operation_guards as guards

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("case", ["deep-json", "oversized-unicode", "invalid-utf8"])
def test_cli_rejects_malformed_or_oversized_requests_without_traceback(case):
    """The public router preserves ERROR semantics at its binary input boundary."""
    payloads = {
        "deep-json": b'{"operation":"read","path":'
        + b"[" * 10000
        + b'"private-parser-sentinel"'
        + b"]" * 10000
        + b"}",
        "oversized-unicode": json.dumps(
            {"operation": "read", "path": "я" * 33000}, ensure_ascii=False
        ).encode("utf-8"),
        "invalid-utf8": b"\xff",
    }
    root = Path(__file__).resolve().parents[4]
    result = subprocess.run(
        [sys.executable, "-B", "-m", "scripts.engineering.repo", "guard-operation"],
        cwd=root,
        input=payloads[case],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "ERROR"
    assert not result.stderr
    assert b"private-parser-sentinel" not in result.stdout


@pytest.mark.parametrize("operation", ["write", "create", "delete", "rename", "move"])
@pytest.mark.parametrize(
    "name", [".env", ".env.local", ".env.example", ".ENV.PRODUCTION", "production.env"]
)
def test_environment_mutations_are_denied(operation: str, name: str) -> None:
    """All mutation kinds protect both secret-bearing and example names."""
    request = {
        "operation": operation,
        "path": f"D:\\workspace\\{name}",
        "destination": "safe.py",
    }
    assert guards.evaluate_request(request).status == "FAIL"


def test_reads_and_ordinary_source_writes_are_allowed() -> None:
    """The environment rule permits reads and does not freeze product code."""
    assert (
        guards.evaluate_request({"operation": "read", "path": ".env"}).status == "PASS"
    )
    assert (
        guards.evaluate_request({"operation": "write", "path": "src/example.py"}).status
        == "PASS"
    )


def test_rename_destination_cannot_hide_environment_mutation() -> None:
    """Moving an ordinary file into a protected name is still a mutation."""
    result = guards.evaluate_request(
        {"operation": "rename", "path": "safe.txt", "destination": ".env.production"}
    )
    assert result.status == "FAIL"


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {"operation": []},
        {"operation": "execute", "path": "python"},
        {"operation": "write", "path": ""},
        {"operation": "move", "path": "a"},
        {"operation": "write", "path": "bad\x00path"},
        {"operation": "write", "path": ".env", "approval": True},
    ],
)
def test_unknown_requests_and_self_grants_are_errors(payload: object) -> None:
    """Malformed requests cannot grant permission or fall through as success."""
    assert guards.evaluate_request(payload).status == "ERROR"


def test_resolved_alias_is_checked_without_creating_env_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An innocent lexical name cannot hide a resolved protected target."""
    monkeypatch.setattr(Path, "resolve", lambda *args, **kwargs: Path("/virtual/.env"))
    assert (
        guards.evaluate_request({"operation": "write", "path": "alias"}).status
        == "FAIL"
    )


def test_path_failure_does_not_echo_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dependency errors must not publish values from exception messages."""

    def fail(*args: object, **kwargs: object) -> Path:
        raise OSError("private-value-must-not-escape")

    monkeypatch.setattr(Path, "resolve", fail)
    result = guards.evaluate_request({"operation": "write", "path": "ordinary"})
    assert result.status == "ERROR"
    assert "private-value" not in json.dumps(asdict(result))


def _workspace(tmp_path: Path) -> Path:
    """Build directories only, never a real checkout or worktree."""
    root = tmp_path / "allowed"
    (root / "BioactivityDataAcquisition-worktrees").mkdir(parents=True)
    return root


def test_worktree_destination_is_checked_twice_without_execution(
    tmp_path: Path,
) -> None:
    """A valid task slug yields evidence and leaves the destination absent."""
    root = _workspace(tmp_path)
    permit = guards.prepare_worktree("task-1", allowed_root=root)
    assert guards.revalidate_worktree(permit, allowed_root=root).status == "PASS"
    assert not permit.canonical.exists()


@pytest.mark.parametrize("destination", ["../escape", "nul", "CON.txt", "nested/task"])
def test_invalid_task_names_are_denied(tmp_path: Path, destination: str) -> None:
    """Traversal and Windows device names must not become destinations."""
    root = _workspace(tmp_path)
    result = guards.evaluate_request(
        {"operation": "worktree_create", "destination": destination}, allowed_root=root
    )
    assert result.status in {"FAIL", "ERROR"}


def test_ancestor_replacement_invalidates_permit(tmp_path: Path) -> None:
    """A renamed/replaced parent is different even if its text path is equal."""
    root = _workspace(tmp_path)
    permit = guards.prepare_worktree("task", allowed_root=root)
    parent = root / "BioactivityDataAcquisition-worktrees"
    parent.rename(root / "previous-parent")
    parent.mkdir()
    assert guards.revalidate_worktree(permit, allowed_root=root).status == "FAIL"


def test_parallel_sibling_creation_does_not_invalidate_permit(tmp_path: Path) -> None:
    """Unrelated agents may create siblings without changing parent identity."""
    root = _workspace(tmp_path)
    permit = guards.prepare_worktree("task", allowed_root=root)
    (permit.requested.parent / "other-task").mkdir()
    assert guards.revalidate_worktree(permit, allowed_root=root).status == "PASS"


def test_directory_alias_cannot_escape_allowed_root(tmp_path: Path) -> None:
    """Real symlinks or Windows junctions are resolved before admission."""
    root = _workspace(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    alias = root / "BioactivityDataAcquisition-worktrees/alias"
    try:
        alias.symlink_to(outside, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            pytest.skip("directory symlinks unavailable")
        env = os.environ.copy()
        env.update(TEST_GUARD_ALIAS=str(alias), TEST_GUARD_TARGET=str(outside))
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path $env:TEST_GUARD_ALIAS -Value $env:TEST_GUARD_TARGET | Out-Null",
            ],
            env=env,
            check=True,
            capture_output=True,
            timeout=10,
        )
    result = guards.evaluate_request(
        {"operation": "worktree_create", "destination": str(alias / "task")},
        allowed_root=root,
    )
    assert result.status == "FAIL"


@pytest.mark.parametrize(
    "name", [".env:stream", ".env. ", ".env ", ".ENV.local:secret"]
)
def test_windows_alias_spellings_are_protected(name: str) -> None:
    """Windows normalization and alternate streams cannot hide env targets."""
    assert (
        guards.evaluate_request({"operation": "write", "path": name}).status == "FAIL"
    )


def test_absolute_nested_destination_is_denied(tmp_path: Path) -> None:
    """Absolute paths cannot bypass the single task-directory rule."""
    root = _workspace(tmp_path)
    nested = root / "BioactivityDataAcquisition-worktrees" / "task" / "nested"
    assert (
        guards.evaluate_request(
            {"operation": "worktree_create", "destination": str(nested)},
            allowed_root=root,
        ).status
        == "FAIL"
    )


@pytest.mark.parametrize("operation", ["delete", "move", "rename", "write"])
def test_directory_mutations_require_host_review(
    tmp_path: Path, operation: str
) -> None:
    """Parent-directory mutations cannot bypass env protection by omission."""
    directory = tmp_path / "ordinary-directory"
    directory.mkdir()
    result = guards.evaluate_request(
        {
            "operation": operation,
            "path": str(directory),
            "destination": str(tmp_path / "moved"),
        }
    )
    assert result.status == "FAIL"
    assert result.code == "path.directory_review"
