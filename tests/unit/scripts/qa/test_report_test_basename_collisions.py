"""The collision writer follows indexed file moves, additions and deletions."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.engineering.qa import report_test_basename_collisions as writer
from scripts.engineering.qa._tracked_glob import git_discovery_environment

pytestmark = pytest.mark.unit


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        env=git_discovery_environment(),
        check=True,
        capture_output=True,
    )


def put(root: Path, path: str, *, tracked: bool = True) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# fixture\n", encoding="utf-8")
    if tracked:
        git(root, "add", "--", path)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init")
    return root


def run(root: Path, mode: str) -> int:
    return writer.main(["--root", str(root), mode])


def read(root: Path) -> dict:
    return json.loads((root / writer.DEFAULT_OUTPUT).read_text(encoding="utf-8"))


def test_moves_remove_both_stale_quality_paths(repo: Path) -> None:
    names = ["test_architecture_quality_scorecard.py", "test_primitives.py"]
    for name in names:
        put(repo, f"tests/unit/infrastructure/quality/{name}")
        put(repo, f"tests/architecture/{name}")
    assert run(repo, "--update") == 0
    destination = repo / "tests/unit/scripts/engineering/quality"
    destination.mkdir(parents=True)
    for name in names:
        git(
            repo,
            "mv",
            f"tests/unit/infrastructure/quality/{name}",
            f"tests/unit/scripts/engineering/quality/{name}",
        )
    assert run(repo, "--check") == 1
    assert run(repo, "--update") == 0
    assert read(repo) == {
        "duplicate_basename_count": 2,
        "duplicate_basenames": {
            name: [
                f"tests/architecture/{name}",
                f"tests/unit/scripts/engineering/quality/{name}",
            ]
            for name in names
        },
    }
    assert run(repo, "--check") == 0


def test_add_delete_and_discovery_contract(repo: Path) -> None:
    put(repo, "tests/a/test_same.py")
    put(repo, "tests/b/test_same.py")
    put(repo, "tests/c/test_same.py", tracked=False)
    put(repo, "tests/a/conftest.py")
    put(repo, "tests/b/conftest.py")
    put(repo, "scripts/test_same.py")
    assert run(repo, "--update") == 0
    assert read(repo) == {
        "duplicate_basename_count": 1,
        "duplicate_basenames": {
            "test_same.py": ["tests/a/test_same.py", "tests/b/test_same.py"]
        },
    }
    git(repo, "add", "--", "tests/c/test_same.py")
    assert run(repo, "--check") == 1
    assert run(repo, "--update") == 0
    assert read(repo)["duplicate_basenames"]["test_same.py"] == [
        "tests/a/test_same.py",
        "tests/b/test_same.py",
        "tests/c/test_same.py",
    ]
    # A missing indexed file must not be reported as existing.
    (repo / "tests/b/test_same.py").unlink()
    git(repo, "rm", "--cached", "--", "tests/c/test_same.py")
    assert run(repo, "--check") == 1
    assert run(repo, "--update") == 0
    assert read(repo) == {"duplicate_basename_count": 0, "duplicate_basenames": {}}


@pytest.mark.parametrize(
    "corruption", ["wrong_path", "missing", "extra", "count", "basename"]
)
def test_check_rejects_wrong_inventory_without_writing(
    repo: Path, corruption: str
) -> None:
    put(repo, "tests/a/test_same.py")
    put(repo, "tests/b/test_same.py")
    assert run(repo, "--update") == 0
    payload = read(repo)
    if corruption == "wrong_path":
        payload["duplicate_basenames"]["test_same.py"][0] = "tests/missing/test_same.py"
    elif corruption == "missing":
        payload["duplicate_basenames"] = {}
    elif corruption == "extra":
        payload["duplicate_basenames"]["test_extra.py"] = ["tests/a/test_extra.py"]
    elif corruption == "count":
        payload["duplicate_basename_count"] = 0
    else:
        payload["duplicate_basenames"]["wrong.py"] = payload["duplicate_basenames"].pop(
            "test_same.py"
        )
    output = repo / writer.DEFAULT_OUTPUT
    output.write_text(json.dumps(payload), encoding="utf-8")
    before = (output.read_bytes(), output.stat().st_mtime_ns)
    assert run(repo, "--check") == 1
    assert (output.read_bytes(), output.stat().st_mtime_ns) == before


def test_check_missing_and_idempotent_update_from_external_cwd(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert run(repo, "--check") == 1
    assert not (repo / "reports").exists()
    assert run(repo, "--update") == 0
    output = repo / writer.DEFAULT_OUTPUT
    before = (output.read_bytes(), output.stat().st_mtime_ns)
    assert run(repo, "--update") == 0
    assert run(repo, "--check") == 0
    assert (output.read_bytes(), output.stat().st_mtime_ns) == before


def test_qa_router_exposes_supported_modes(repo: Path) -> None:
    from scripts.engineering.qa.__main__ import main

    assert (
        main(["report-test-basename-collisions", "--root", str(repo), "--update"]) == 0
    )
    assert (
        main(["report-test-basename-collisions", "--root", str(repo), "--check"]) == 0
    )
